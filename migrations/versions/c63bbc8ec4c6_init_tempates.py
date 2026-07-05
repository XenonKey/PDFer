"""add initial templates

Revision ID: c63bbc8ec4c6
Revises: 49aec835a13c
Create Date: 2026-06-27 16:26:00.000000

"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# Идентификаторы ревизий Alembic
revision = "c63bbc8ec4c6"
down_revision = "49aec835a13c"
branch_labels = None
depends_on = None

# Имя таблицы
table_name = "templates"


def upgrade() -> None:
    # Полное определение структуры для безопасной вставки данных
    templates_table = sa.table(
        table_name,
        sa.column("id", sa.UUID),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.String),
        sa.column("schema", JSONB),
        sa.column("html_template", sa.String),
    )

    # Вставка демонстрационных данных
    op.bulk_insert(
        templates_table,
        [
            {
                "id": uuid.uuid4(),
                "name": "Договор оказания услуг",
                "slug": "service-agreement",
                "description": "Стандартный договор с физическими и юридическими лицами",
                "schema": {
                    "type": "object",
                    "properties": {
                        "client_name": {"type": "string", "title": "Имя клиента"},
                        "price": {"type": "number", "title": "Стоимость услуг"},
                    },
                    "required": ["client_name", "price"],
                },
                "html_template": "<h1>Договор</h1><p>Исполнитель обязуется оказать услуги для {{ client_name }} на сумму {{ price }} руб.</p>",
            },
            {
                "id": uuid.uuid4(),
                "name": "Счет на оплату",
                "slug": "invoice",
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
            {
                "id": uuid.uuid4(),
                "name": "Акт выполненных работ",
                "slug": "completion-act",
                "description": "Документ, подтверждающий выполнение обязательств",
                "schema": {
                    "type": "object",
                    "properties": {
                        "act_date": {"type": "string", "title": "Дата акта"},
                        "job_description": {
                            "type": "string",
                            "title": "Описание работ",
                        },
                    },
                    "required": ["act_date", "job_description"],
                },
                "html_template": "<h1>Акт от {{ act_date }}</h1><p>Работы выполнены в полном объеме: {{ job_description }}</p>",
            },
        ],
    )


def downgrade() -> None:
    # Удаление добавленных записей по их уникальным slug
    op.execute(f"DELETE FROM {table_name} WHERE slug IN ('service-agreement', 'invoice', 'completion-act')")
