import reflex as rx


def index() -> rx.Component:
    return rx.container(
        rx.heading("example", size="7"),
        rx.text("Generated from scraped DuckDB/Parquet data."),
        rx.link("API health", href="http://localhost:8000/health"),
        padding="2rem",
    )

app = rx.App()
app.add_page(index)
