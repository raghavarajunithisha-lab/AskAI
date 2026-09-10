import json
from ollama_client import call_ollama
from config import TEXT_MODEL, VISION_MODEL

from image_reader import prepare_image, ask_image
from ocr_reader import read_image_text
from file_chat import answer_question



ROUTE_SCHEMA = {
    "type": "object",
    "properties": {
        "route": {
            "type": "string",
            "enum": ["text", "vision", "both", "clarify"],
        },
        "question": {"type": "string"},
    },
    "required": ["route", "question"],
    "additionalProperties": False,
}


def unload_model(model):
    # Release model memory without deleting its downloaded files.
    call_ollama("generate", {
        "model": model,
        "keep_alive": 0,
        "stream": False,
    })


def choose_tools(question, history, ocr_status):
    instructions = (
        "Choose tools for a question about a selected image. "
        "Available routes:\n"
        "text: read visible writing, summarize a document or poster, "
        "or answer questions about its written content.\n"
        "vision: inspect objects, clothing, colors, appearance "
        "or other visual details.\n"
        "both: combine written content with visual information, "
        "or give a general explanation of an image of unknown type.\n"
        "clarify: the request is unclear or asks for an unsupported "
        "action such as editing, converting or generating an image.\n"
        "OCR is available but can contain mistakes. "
        "If OCR is unavailable, use vision to attempt text reading "
        "when relevant; do not assume the image has no text.\n"
        "Use conversation history only to resolve follow-up references. "
        "For a supported request, question must be a standalone version "
        "of the user's question, preserving its meaning. "
        "Do not add facts from previous answers as assumptions. "
        "For clarify, question must ask the user what is needed or "
        "explain that this entry point currently answers questions only. "
        "Return JSON matching the schema."
    )

    response = call_ollama("chat", {
        "model": TEXT_MODEL,
        "stream": False,
        "think": False,
        "format": ROUTE_SCHEMA,
        # Release Qwen after routing to leave room for vision.
        "keep_alive": 0,
        "options": {
            "temperature": 0,
            "num_ctx": 4096,
            "num_predict": 300,
        },
        "messages": [
            {"role": "system", "content": instructions},
            {
                "role": "user",
                "content": json.dumps({
                    "ocr_status": ocr_status,
                    "recent_conversation": history[-4:],
                    "request": question,
                }, ensure_ascii=False),
            },
        ],
    })

    decision = json.loads(response["message"]["content"])

    if not isinstance(decision, dict):
        raise ValueError("The model returned an invalid tool choice.")

    if set(decision) != {"route", "question"}:
        raise ValueError("The model returned unexpected fields.")

    if decision["route"] not in {
        "text", "vision", "both", "clarify"
    }:
        raise ValueError("The model selected an unavailable tool.")

    if not isinstance(decision["question"], str):
        raise ValueError("The model returned an invalid question.")

    if not decision["question"].strip():
        raise ValueError("The model returned an empty question.")

    return decision


def answer_image_question(
    encoded_image,
    ocr_result,
    ocr_status,
    question,
    history,
):
    decision = choose_tools(question, history, ocr_status)

    if decision["route"] == "clarify":
        history.extend([{ "role": "user", "content": question},
                        {"role": "assistant", "content": decision["question"][:1500]}])
        del history[:-4]
        return decision["question"]

    route = decision["route"]
    standalone_question = decision["question"]

    # If text extraction failed, let vision attempt the question.
    if route == "text" and ocr_status != "text_available":
        route = "vision"

    evidence = []
    partial = False

    if route in {"text", "both"}:
        if ocr_status == "text_available":
            text = ocr_result["content"]

            # Reserve space for visual observations when using both.
            limit = 3500 if route == "both" else 5500
            partial = len(text) > limit

            evidence.append(
                "OCR TEXT — may contain errors or mix columns:\n"
                + text[:limit]
            )
        else:
            evidence.append(
                "OCR did not supply readable text. "
                "This does not establish that the image has no text."
            )

    if route in {"vision", "both"}:
        print("Examining the image...")

        try:
            visual_answer = ask_image(
                encoded_image,
                standalone_question,
            )
        finally:
            # Avoid keeping both models loaded on the 4 GB GPU.
            try:
                unload_model(VISION_MODEL)
            except Exception:
                print("Could not unload the vision model; its normal idle timeout still applies.")

        partial = partial or len(visual_answer) > 2000

        evidence.append(
            "VISION MODEL OBSERVATIONS — unverified and possibly "
            "inaccurate, not established facts:\n"
            + visual_answer[:2000]
        )

    document = {
        "content": "\n\n".join(evidence),
        "partial": partial,
        "scope": (
            "Evidence from tools examining one selected image. "
            "OCR can misread letters, omit text, or mix columns. "
            "Vision observations may contain invented details. "
            "For exact wording, prefer readable OCR over guesses. "
            "For appearance, use visual observations cautiously. "
            "If the evidence conflicts, explain the uncertainty. "
            "Do not invent diagram connections or missing details. "
            "Do not discuss tool implementation unless asked."
        ),
    }

    print("Preparing the answer...")

    return answer_question(
        document,
        question,
        history,
    )


def main():
    selected = input(
        "Paste an image path: "
    ).strip().strip('"')

    try:
        encoded_image = prepare_image(selected)
    except Exception as error:
        print(f"Could not open the image: {error}")
        return

    # OCR runs once per image, not once per question.
    print("Checking the image for readable text...")

    ocr_result = None

    try:
        ocr_result = read_image_text(selected)

        ocr_status = (
            "no_text_recognized"
            if ocr_result["no_text_detected"]
            else "text_available"
        )

        if ocr_status == "text_available":
            print("Image text is available.")
        else:
            print("OCR recognized no text. Visual questions are available.")

    except Exception as error:
        ocr_status = "unavailable"
        print(f"OCR could not run: {error}")
        print("Visual questions are still available.")

    history = []

    print("\nReady. Ask about the image.")
    print("Type /clear to clear history or /exit to finish.")

    while True:
        question = input("\nYou: ").strip()

        if question.lower() == "/exit":
            break

        if question.lower() == "/clear":
            history.clear()
            print("History cleared. The selected image is retained.")
            continue

        if not question:
            continue

        if len(question) > 1000:
            print("Please keep questions under 1,000 characters.")
            continue

        try:
            answer = answer_image_question(
                encoded_image,
                ocr_result,
                ocr_status,
                question,
                history,
            )

            print("\nAskAI:", answer)

        except Exception as error:
            print(f"Could not answer: {error}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nImage chat closed.")