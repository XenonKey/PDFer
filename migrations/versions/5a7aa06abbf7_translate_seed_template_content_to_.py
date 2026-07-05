"""translate seed template content to english

Revision ID: 5a7aa06abbf7
Revises: b160868a1836
Create Date: 2026-07-05 06:27:52.206467

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "5a7aa06abbf7"
down_revision: Union[str, None] = "b160868a1836"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

templates_table = sa.table(
    "templates",
    sa.column("slug", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("schema", JSONB),
    sa.column("html_template", sa.String),
)

EN_CONTENT = {
    "service-agreement": {
        "name": "Service Agreement",
        "description": "Standard agreement with individuals and legal entities",
        "schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "title": "Client Name"},
                "price": {"type": "number", "title": "Service Price"},
            },
            "required": ["client_name", "price"],
        },
        "html_template": (
            "<h1>Service Agreement</h1>"
            "<p>The provider agrees to render services for {{ client_name }} for a total of {{ price }}.</p>"
        ),
    },
    "invoice": {
        "name": "Invoice",
        "description": "Invoice for payment of goods or services",
        "schema": {
            "type": "object",
            "properties": {
                "invoice_num": {"type": "string", "title": "Invoice Number"},
                "amount": {"type": "number", "title": "Amount"},
            },
            "required": ["invoice_num", "amount"],
        },
        "html_template": "<h1>Invoice #{{ invoice_num }}</h1><p>Amount due: {{ amount }}.</p>",
    },
    "completion-act": {
        "name": "Certificate of Completion",
        "description": "Document confirming that obligations have been fulfilled",
        "schema": {
            "type": "object",
            "properties": {
                "act_date": {"type": "string", "title": "Certificate Date"},
                "job_description": {"type": "string", "title": "Description of Work"},
            },
            "required": ["act_date", "job_description"],
        },
        "html_template": (
            "<h1>Certificate of Completion dated {{ act_date }}</h1>"
            "<p>Work has been completed in full: {{ job_description }}.</p>"
        ),
    },
}

RU_CONTENT = {
    "service-agreement": {
        "name": "Договор оказания услуг",
        "description": "Стандартный договор с физическими и юридическими лицами",
        "schema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "title": "Имя клиента"},
                "price": {"type": "number", "title": "Стоимость услуг"},
            },
            "required": ["client_name", "price"],
        },
        "html_template": (
            "<h1>Договор</h1><p>Исполнитель обязуется оказать услуги для {{ client_name }} "
            "на сумму {{ price }} руб.</p>"
        ),
    },
    "invoice": {
        "name": "Счет на оплату",
        "description": "Счет для оплаты товаров или услуг",
        "schema": {
            "type": "object",
            "properties": {
                "invoice_num": {"type": "string", "title": "Номер счета"},
                "amount": {"type": "number", "title": "Сумма"},
            },
            "required": ["invoice_num", "amount"],
        },
        "html_template": "<h1>Счет № {{ invoice_num }}</h1><p>К оплате: {{ amount }} руб.</p>",
    },
    "completion-act": {
        "name": "Акт выполненных работ",
        "description": "Документ, подтверждающий выполнение обязательств",
        "schema": {
            "type": "object",
            "properties": {
                "act_date": {"type": "string", "title": "Дата акта"},
                "job_description": {"type": "string", "title": "Описание работ"},
            },
            "required": ["act_date", "job_description"],
        },
        "html_template": "<h1>Акт от {{ act_date }}</h1><p>Работы выполнены в полном объеме: {{ job_description }}</p>",
    },
}


def _apply(content: dict) -> None:
    for slug, fields in content.items():
        op.execute(
            templates_table.update()
            .where(templates_table.c.slug == slug)
            .values(
                name=fields["name"],
                description=fields["description"],
                schema=fields["schema"],
                html_template=fields["html_template"],
            )
        )


def upgrade() -> None:
    _apply(EN_CONTENT)


def downgrade() -> None:
    _apply(RU_CONTENT)
