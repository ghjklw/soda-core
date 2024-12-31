from __future__ import annotations

from soda_core.common.data_source import DataSource
from soda_core.common.sql_dialect import *
from soda_core.common.yaml import YamlObject
from soda_core.contracts.contract_verification import CheckResult, CheckOutcome
from soda_core.contracts.impl.check_types.row_count_check_type import RowCountMetric
from soda_core.contracts.impl.column_configurations import MissingConfigurations
from soda_core.contracts.impl.contract_verification_impl import MetricsResolver, Check, AggregationMetric, Threshold, \
    ThresholdType, DerivedPercentageMetric
from soda_core.contracts.impl.contract_yaml import CheckYaml, ColumnYaml, ContractYaml, CheckType
from soda_core.tests.features.test_missing_check import missing_no_rows_specification


class MissingCheckType(CheckType):

    def get_check_type_names(self) -> list[str]:
        return ['missing_count', 'missing_percent']

    def parse_check_yaml(
        self,
        check_yaml_object: YamlObject,
        column_yaml: ColumnYaml | None,
    ) -> CheckYaml | None:
        return MissingCheckYaml(
            check_yaml_object=check_yaml_object,
        )


class MissingCheckYaml(CheckYaml):

    def __init__(
        self,
        check_yaml_object: YamlObject,
    ):
        super().__init__(
            check_yaml_object=check_yaml_object
        )
        self.parse_threshold(check_yaml_object)

    def create_check(self, data_source: DataSource, dataset_prefix: list[str] | None, contract_yaml: ContractYaml,
                     column_yaml: ColumnYaml | None, check_yaml: CheckYaml, metrics_resolver: MetricsResolver) -> Check:
        return MissingCheck(
            data_source=data_source,
            dataset_prefix=dataset_prefix,
            contract_yaml=contract_yaml,
            column_yaml=column_yaml,
            check_yaml=self,
            metrics_resolver=metrics_resolver,
        )


class MissingCheck(Check):

    def __init__(
        self,
        data_source: DataSource,
        dataset_prefix: list[str] | None,
        contract_yaml: ContractYaml,
        column_yaml: ColumnYaml | None,
        check_yaml: MissingCheckYaml,
        metrics_resolver: MetricsResolver,
    ):
        threshold = Threshold.create(check_yaml=check_yaml, default_threshold=Threshold(
            type=ThresholdType.SINGLE_COMPARATOR,
            must_be=0
        ))
        summary = (threshold.get_assertion_summary(metric_name=check_yaml.type)
                   if threshold else f"{check_yaml.type} (invalid threshold)")
        super().__init__(
            contract_yaml=contract_yaml,
            column_yaml=column_yaml,
            check_yaml=check_yaml,
            dataset_prefix=dataset_prefix,
            threshold=threshold,
            summary=summary
        )

        missing_configurations: MissingConfigurations = column_yaml.get_missing_configurations()

        missing_count_metric = MissingCountMetric(
            data_source_name=self.data_source_name,
            dataset_prefix=self.dataset_prefix,
            dataset_name=self.dataset_name,
            column_name=self.column_name,
            missing_configurations=missing_configurations
        )
        resolved_missing_count_metric: MissingCountMetric = metrics_resolver.resolve_metric(missing_count_metric)
        self.metrics["missing_count"] = resolved_missing_count_metric
        self.aggregation_metrics.append(resolved_missing_count_metric)

        if self.type == "missing_percent":
            row_count_metric = RowCountMetric(
                data_source_name=self.data_source_name,
                dataset_prefix=self.dataset_prefix,
                dataset_name=self.dataset_name
            )
            resolved_row_count_metric: RowCountMetric = metrics_resolver.resolve_metric(row_count_metric)
            self.metrics["row_count"] = resolved_row_count_metric
            self.aggregation_metrics.append(resolved_row_count_metric)

            self.metrics["missing_percent"] = DerivedPercentageMetric(
                metric_name="missing_percent",
                fraction_metric=resolved_missing_count_metric,
                total_metric=resolved_row_count_metric
            )

    def evaluate(self) -> CheckResult:
        outcome: CheckOutcome = CheckOutcome.NOT_EVALUATED

        missing_count: int = self.metrics["missing_count"].value
        diagnostic_lines = [
            f"Actual missing_count was {missing_count}"
        ]

        threshold_value: Number | None = None
        if self.type == "missing_count":
            threshold_value = missing_count
        else:
            row_count: int = self.metrics["row_count"].value
            diagnostic_lines.append(f"Actual row_count was {row_count}")
            if row_count > 0:
                missing_percent: float = self.metrics["missing_percent"].value
                diagnostic_lines.append(f"Actual missing_percent was {missing_percent}")
                threshold_value = missing_percent

        if self.threshold and isinstance(threshold_value, Number):
            if self.threshold.passes(threshold_value):
                outcome = CheckOutcome.PASSED
            else:
                outcome = CheckOutcome.FAILED

        return CheckResult(
            outcome=outcome,
            check_summary=self.summary,
            diagnostic_lines=diagnostic_lines,
        )


class MissingCountMetric(AggregationMetric):

    def __init__(
        self,
        data_source_name: str,
        dataset_prefix: list[str] | None,
        dataset_name: str,
        column_name: str,
        missing_configurations: MissingConfigurations
    ):
        super().__init__(
            data_source_name=data_source_name,
            dataset_prefix=dataset_prefix,
            dataset_name=dataset_name,
            column_name=column_name,
            metric_type_name="missing_count"
        )
        self.missing_configurations = missing_configurations

    def sql_expression(self) -> SqlExpression:
        is_missing_clauses: list[SqlExpression] = [IS_NULL(self.column_name)]
        if isinstance(self.missing_configurations.missing_values, list):
            literal_values = [LITERAL(value) for value in self.missing_configurations.missing_values]
            is_missing_clauses.append(IN(self.column_name, literal_values))
        ...TODO like regex...
        return SUM(CASE_WHEN(OR(is_missing_clauses), LITERAL(1), LITERAL(0)))

    def set_value(self, value):
        # expression SUM(CASE WHEN "id" IS NULL THEN 1 ELSE 0 END) gives NULL / None as a result if there are no rows
        value = 0 if value is None else value
        self.value = int(value)
