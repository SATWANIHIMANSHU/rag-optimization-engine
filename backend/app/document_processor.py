from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption


PROCESSED_DIR = Path("data/processed")


def process_pdf(file_path):
    """
    Process a PDF using Docling.

    Produces:
    - structured Markdown
    - tables
    - figures/images
    - page information
    """

    file_path = Path(file_path)

    output_dir = PROCESSED_DIR / file_path.stem

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    pipeline_options = PdfPipelineOptions()

    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    pipeline_options.generate_picture_images = True
    pipeline_options.generate_page_images = False

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options
            )
        }
    )

    result = converter.convert(file_path)

    document = result.document

    # --------------------------------------------------
    # MARKDOWN
    # --------------------------------------------------

    markdown = document.export_to_markdown()

    markdown_path = output_dir / "document.md"

    with open(
        markdown_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(markdown)

    # --------------------------------------------------
    # TABLES
    # --------------------------------------------------

    tables = []

    for index, table in enumerate(
        document.tables,
        start=1
    ):

        try:
            table_markdown = table.export_to_markdown(
                doc=document
            )

        except Exception:
            table_markdown = ""

        try:
            table_html = table.export_to_html(
                doc=document
            )

        except Exception:
            table_html = ""

        table_info = {
            "index": index,
            "markdown": table_markdown,
            "html": table_html
        }

        tables.append(table_info)

        table_md_path = (
            output_dir /
            f"table_{index}.md"
        )

        with open(
            table_md_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(table_markdown)

        table_html_path = (
            output_dir /
            f"table_{index}.html"
        )

        with open(
            table_html_path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(table_html)

    # --------------------------------------------------
    # FIGURES / IMAGES
    # --------------------------------------------------

    figures = []

    for index, picture in enumerate(
        document.pictures,
        start=1
    ):

        try:

            image = picture.get_image(
                document
            )

            if image is None:
                continue

            image_path = (
                output_dir /
                f"figure_{index}.png"
            )

            image.save(
                image_path,
                "PNG"
            )

            figures.append({
                "index": index,
                "path": str(image_path)
            })

        except Exception as error:

            print(
                f"Could not extract figure {index}: {error}"
            )

    # --------------------------------------------------
    # RESULT
    # --------------------------------------------------

    return {
        "source": file_path.name,
        "markdown": markdown,
        "markdown_path": str(markdown_path),
        "tables": tables,
        "figures": figures
    }