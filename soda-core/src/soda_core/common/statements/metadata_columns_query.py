from __future__ import annotations

from soda_core.common.data_source_connection import DataSourceConnection
from soda_core.common.data_source_results import QueryResult
from soda_core.common.sql_dialect import *


@dataclass
class MetadataColumn:
    column_name: str
    data_type: str


class MetadataColumnsQuery:

    def __init__(
        self,
        sql_dialect: SqlDialect,
        data_source_connection: DataSourceConnection
    ):
        self.sql_dialect = sql_dialect
        self.data_source_connection: DataSourceConnection = data_source_connection

    def build_sql(
        self,
        database_name: str,
        schema_name: str,
        dataset_name: str
    ) -> str:
        """
        Builds the full SQL query to query table names from the data source metadata.
        """
        return self.sql_dialect.build_select_sql([
            SELECT([
                self._column_column_name(),
                self._column_data_type()]),
            FROM(self._table_columns()).IN([database_name, self._schema_information_schema()]),
            WHERE(AND([
                EQ(self._column_table_catalog(), LITERAL(database_name)),
                EQ(self._column_table_schema(), LITERAL(schema_name)),
                EQ(self._column_table_name(), LITERAL(dataset_name))
            ])),
        ])

    def get_result(self, query_result: QueryResult) -> list[MetadataColumn]:
        return [
            MetadataColumn(
                column_name=column_name,
                data_type=data_type
            )
            for column_name, data_type in query_result.rows
        ]

    def _schema_information_schema(self) -> str:
        """
        Name of the schema that has the metadata.
        Purpose of this method is to allow specific data source to override.
        """
        return "information_schema"

    def _table_columns(self) -> str:
        """
        Name of the table that has the columns information in the metadata.
        Purpose of this method is to allow specific data source to override.
        """
        return "columns"

    def _column_table_catalog(self) -> str:
        """
        Name of the column that has the database information in the tables metadata table.
        Purpose of this method is to allow specific data source to override.
        """
        return "table_catalog"

    def _column_table_schema(self) -> str:
        """
        Name of the column that has the schema information in the tables metadata table.
        Purpose of this method is to allow specific data source to override.
        """
        return "table_schema"

    def _column_table_name(self) -> str:
        """
        Name of the column that has the table name in the tables metadata table.
        Purpose of this method is to allow specific data source to override.
        """
        return "table_name"

    def _column_column_name(self) -> str:
        """
        Name of the column that has the column name in the tables metadata table.
        Purpose of this method is to allow specific data source to override.
        """
        return "column_name"

    def _column_data_type(self) -> str:
        """
        Name of the column that has the data type in the tables metadata table.
        Purpose of this method is to allow specific data source to override.
        """
        return "data_type"
