import tempfile
from unittest.mock import patch

import pytest

from multiqc import report, Plot, config
from multiqc.core.exceptions import RunError
from multiqc.plots import bargraph, linegraph, table, violin, heatmap, scatter, box
from multiqc.plots.plotly.line import Series, LinePlotConfig
from multiqc.validation import ConfigValidationError


def test_barplot():
    """
    Normal barplot call. Single datasets, a list of cats, some cats are excluded.
    """
    plot_id = "test_barplot"

    plot = bargraph.plot(
        {
            "Sample0": {},
            "Sample1": {"Cat1": 1},
            "Sample2": {"Cat1": 1, "Cat2": 1},
            "Sample3": {"Cat1": 1, "Cat2": 1, "Cat3": 1},
        },
        ["Cat1", "Cat2"],
        {"id": plot_id, "title": "Test: Bar Graph"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data


def test_bar_plot_no_matching_cats():
    """
    None of the cats are matching thd data, so shouldn't produce a plot
    """
    plot_id = "test_bar_plot_no_matching_cats"

    plot = bargraph.plot(
        {"Sample1": {"Cat0": 1, "Cat1": 1}},
        ["Cat2", "Cat3"],
        {"id": plot_id, "title": "Test: Bar Graph"},
    )
    # Will return a warning message html instead of a plot:
    assert isinstance(plot, str)


def test_bar_plot_cats_dicts():
    """
    Advanced cats spec - dict with cat properties instead of a simple list
    """
    plot_id = "test_bar_plot_cats_dicts"

    plot = bargraph.plot(
        {"Sample1": {"Cat1": 1}},
        {"Cat1": {"name": "My category"}},
        {"id": plot_id, "title": "Test: Bar Graph"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert report.plot_data[plot_id]["datasets"][0]["cats"][0]["name"] == "My category"


def test_bar_plot_cats_dicts_with_typo():
    """
    A typo in the cat properties dict - will fill in the name from the dict key
    """
    plot_id = "test_bar_plot_cats_dicts_with_typo"

    plot = bargraph.plot(
        {"Sample1": {"Cat1": 2}},
        {"Cat1": {"name_with_typo": "My category"}},
        {"id": plot_id, "title": "Test: Bar Graph"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert report.plot_data[plot_id]["datasets"][0]["cats"][0]["name"] == "Cat1"


def test_bar_plot_cats_mismatch_cats_and_ds_count():
    """
    Multiple datasets, but the list lengths are not matching between data and cats. Should throw an error
    """
    plot_id = "test_bar_plot_cats_mismatch_cats_and_ds_count"

    with pytest.raises(RunError):
        bargraph.plot(
            [{"Sample1": {"Cat1": 2}}],
            [{"Cat1": {"name": "My category"}}, {"Cat1": {"name": "My category"}}],
            {"id": plot_id, "title": "Test: Bar Graph"},
        )


def test_bar_plot_fill_cats():
    """
    Multiple datasets, but only one dict of cats - in this case, should copy these cats between datasets
    """
    plot_id = "test_bar_plot_fill_cats"

    plot = bargraph.plot(
        [{"Sample1": {"Cat1": 2, "Cat2": 2}}, {"Sample1": {"Cat1": 2, "Cat3": 2}}],
        {"Cat1": {"name": "My category"}},
        {"id": plot_id, "title": "Test: Bar Graph"},
    )
    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data[plot_id]["datasets"]) == 2
    assert len(report.plot_data[plot_id]["datasets"][0]["cats"]) == 1
    assert len(report.plot_data[plot_id]["datasets"][1]["cats"]) == 1
    assert report.plot_data[plot_id]["datasets"][0]["cats"][0]["name"] == "My category"
    assert report.plot_data[plot_id]["datasets"][1]["cats"][0]["name"] == "My category"


def test_bar_plot_no_cats():
    """
    Cats parameter is missing, will fill in one from the data
    """

    plot_id = "test_bar_plot_no_cats"

    plot = bargraph.plot(
        {
            "Sample1": {"Cat1": 2, "Cat2": 2},
            "Sample2": {"Cat1": 1, "Cat3": 1},
        },
        pconfig={"id": plot_id, "title": "Test: Bar Graph"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data[plot_id]["datasets"][0]["cats"]) == 3


def test_linegraph():
    plot_id = "test_linegraph"

    dataset = {
        "Sample0": {},
        "Sample1": {0: 1, 1: 1},
        "Sample2": {0: 1, 1: 1, 2: 1},
    }

    plot = linegraph.plot(
        dataset,
        {"id": plot_id, "title": "Test: Line Graph"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data

    for in_series, out_series in zip(dataset.values(), report.plot_data[plot_id]["datasets"][0]["lines"]):
        assert len(in_series) == len(out_series["pairs"])


def test_linegraph_smooth():
    plot_id = "test_linegraph_smooth"
    SMOOTH_TO = 2
    dataset = {"Smoothed": {0: 1, 1: 1, 2: 1}, "Unsmoothed": {0: 1, 1: 1}}
    plot = linegraph.plot(
        dataset,
        {"id": plot_id, "title": "Test: Line Graph", "smooth_points": SMOOTH_TO},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    for in_series, out_series in zip(dataset.values(), report.plot_data[plot_id]["datasets"][0]["lines"]):
        assert min(len(in_series), SMOOTH_TO) == len(out_series["pairs"])


def test_linegraph_multiple_datasets():
    plot_id = "test_linegraph_multiple_datasets"

    plot = linegraph.plot(
        [{"Sample1": {0: 1, 1: 1}}, {"Sample1": {0: 2, 1: 2}}],
        {
            "id": plot_id,
            "title": "Test: Line Graph",
            "data_labels": ["Dataset1", "Dataset2"],
        },
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data[plot_id]["datasets"]) == 2


def test_table():
    plot_id = "test_table"

    plot = table.plot(
        {
            "Sample1": {"Metric1": 1, "Metric2": 2},
            "Sample2": {"Metric1": 3, "Metric2": 4},
        },
        headers={
            "Metric1": {"title": "Metric 1"},
            "Metric2": {"title": "Metric 2"},
        },
        pconfig={"id": plot_id, "title": "Test: Table"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data


def test_violin():
    plot_id = "test_violin"

    plot = violin.plot(
        {
            "Sample1": {"Metric1": 1, "Metric2": 2},
            "Sample2": {"Metric1": 3, "Metric2": 4},
        },
        headers={
            "Metric1": {"title": "Metric 1"},
            "Metric2": {"title": "Metric 2"},
        },
        pconfig={"id": plot_id, "title": "Test: Violin Plot"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data


def test_heatmap():
    plot_id = "test_heatmap"

    plot = heatmap.plot(
        data=[[1, 2], [3, 4]],
        xcats=["Cat1", "Cat2"],
        ycats=["Sample1", "Sample2"],
        pconfig={"id": plot_id, "title": "Test: Heatmap"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data


def test_scatter():
    plot_id = "test_scatter"

    plot = scatter.plot(
        {"Sample1": [{"x": 1, "y": 2}]},
        {
            "id": plot_id,
            "title": "Test: Scatter Plot",
            "xlab": "X",
            "ylab": "Y",
        },
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data


def test_box_plot():
    plot_id = "test_box_plot"

    plot = box.plot(
        {"Sample1": [1, 2, 3], "Sample2": [4, 5, 6]},
        {"id": plot_id, "title": "Test: Box Plot"},
    )

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data


@pytest.mark.parametrize(
    "development,export_plots,export_plot_formats",
    [
        (False, False, None),  # default mode - embed, no export
        (False, True, None),  # embed + export all formats
        (True, True, ["pdf"]),  # link png + export pdf (should also export png for html)
        (True, False, None),  # link png + no export (should only export png)
    ],
)
def test_flat_plot(tmp_path, monkeypatch, development, export_plot_formats, export_plots):
    monkeypatch.setattr(tempfile, "mkdtemp", lambda: tmp_path)
    report.reset()
    config.reset()

    plot_id = "test_plot"
    plot = linegraph.plot({"Sample1": {0: 1, 1: 1}}, {"id": plot_id, "title": "Line Graph"})
    assert isinstance(plot, Plot)

    plot.flat = True
    config.development = development
    config.export_plots = export_plots
    if export_plot_formats:
        config.export_plot_formats = export_plot_formats

    html = plot.add_to_report()

    assert len(report.plot_data) == 0
    assert html is not None
    if not development:
        assert f'<div class="mqc_mplplot" id="{plot_id}"><img src="data:image/png;base64' in html
        if not export_plots:
            for fmt in ["png", "pdf", "svg"]:
                assert not (tmp_path / f"multiqc_plots/{fmt}/{plot_id}.{fmt}").is_file()
    else:
        assert f'<div class="mqc_mplplot" id="{plot_id}"><img src="multiqc_plots/png/{plot_id}.png' in html
        assert (tmp_path / f"multiqc_plots/png/{plot_id}.png").is_file()
        if not export_plots:
            for fmt in ["pdf", "svg"]:
                assert not (tmp_path / f"multiqc_plots/{fmt}/{plot_id}.{fmt}").is_file()
    if export_plots:
        for fmt in export_plot_formats or ["png", "pdf", "svg"]:
            assert (tmp_path / f"multiqc_plots/{fmt}/{plot_id}.{fmt}").is_file()


def test_missing_pconfig(capsys):
    report.reset()
    linegraph.plot({"Sample1": {0: 1, 1: 1}})
    assert report.lint_errors == [
        "pconfig with required fields 'id' and 'title' must be provided for plot LinePlotConfig",
    ]

    plot = linegraph.plot({"Sample1": {0: 1, 1: 1}})
    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    plot_id = list(report.plot_data.keys())[0]
    assert plot_id.startswith("lineplot-")


@pytest.mark.parametrize("strict", [True, False])
def test_incorrect_fields(strict):
    from multiqc import config

    config.strict = strict

    pconfig = {
        "id": "test_incorrect_fields",
        "title": "Test: Line Graph",
        "unknown_field": "value",
        "x_lines": "wrong_type",
    }

    if strict:
        with pytest.raises(ConfigValidationError):
            linegraph.plot({"Sample1": {0: 1, 1: 1}}, pconfig=pconfig)
    else:
        with patch("logging.Logger.error") as err, patch("logging.Logger.warning") as warn:
            plot = linegraph.plot({"Sample1": {0: 1, 1: 1}}, pconfig=pconfig)
            errors = [call.args[0] for call in err.mock_calls if call.args]
            assert "• 'x_lines': failed to parse value 'wrong_type'" in errors
            assert any(e for e in errors if e.startswith("Errors parsing LinePlotConfig"))
            warnings = [call.args[0] for call in warn.mock_calls if call.args]
            assert any(w for w in warnings if w.startswith("• unrecognized field 'unknown_field'"))
        assert isinstance(plot, Plot)
        report.reset()
        plot.add_to_report()
        assert len(report.plot_data) == 1
        assert "test_incorrect_fields" in report.plot_data

    config.strict = False


@pytest.mark.parametrize("strict", [True, False])
def test_missing_id_and_title(strict):
    from multiqc import config

    config.strict = strict
    if strict:
        with pytest.raises(ConfigValidationError):
            linegraph.plot({"Sample1": {0: 1, 1: 1}}, pconfig={})
    else:
        with patch("logging.Logger.error") as log:
            plot = linegraph.plot({"Sample1": {0: 1, 1: 1}}, pconfig={})
            errs = [call.args[0] for call in log.mock_calls if call.args]
            assert "• missing required field 'id'" in errs
            assert "• missing required field 'title'" in errs
        assert isinstance(plot, Plot)
        report.reset()
        plot.add_to_report()
        assert len(report.plot_data) == 1
        plot_id = list(report.plot_data.keys())[0]
        assert plot_id.startswith("lineplot-")

    config.strict = False


def test_incorrect_color():
    plot_id = "my_plot"
    pconfig = {
        "id": plot_id,
        "title": "Line Graph",
        "extra_series": [{"color": "invalid"}],
    }

    with patch("logging.Logger.error") as err:
        plot = linegraph.plot({"Sample1": {0: 1, 1: 1}}, pconfig=pconfig)
        errors = [call.args[0] for call in err.mock_calls if call.args]
        assert "• invalid color value 'invalid'" in errors

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data


def test_extra_series_multiple_datasets():
    """Should zip series with the datasets"""
    plot_id = "my_plot"
    pconfig = LinePlotConfig(
        id=plot_id,
        title="Line Graph",
        extra_series=[Series(pairs=[(1, 2)], name="Extra1")],
    )
    plot = linegraph.plot([{"Sample1": {0: 1, 1: 1}}, {"Sample1": {0: 2, 1: 2}}], pconfig=pconfig)

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()

    assert len(report.plot_data[plot_id]["datasets"][0]["lines"]) == 2
    assert len(report.plot_data[plot_id]["datasets"][0]["lines"][0]["pairs"]) == 2
    assert len(report.plot_data[plot_id]["datasets"][0]["lines"][1]["pairs"]) == 1
    assert report.plot_data[plot_id]["datasets"][0]["lines"][0]["name"] == "Sample1"
    assert report.plot_data[plot_id]["datasets"][0]["lines"][1]["name"] == "Extra1"

    assert len(report.plot_data[plot_id]["datasets"][1]["lines"]) == 2
    assert len(report.plot_data[plot_id]["datasets"][1]["lines"][0]["pairs"]) == 2
    assert len(report.plot_data[plot_id]["datasets"][1]["lines"][1]["pairs"]) == 1
    assert report.plot_data[plot_id]["datasets"][1]["lines"][0]["name"] == "Sample1"
    assert report.plot_data[plot_id]["datasets"][1]["lines"][1]["name"] == "Extra1"


def test_multiple_extra_series():
    """Should add two series to the dataset in addition to the main data"""
    plot_id = "my_plot"
    pconfig = LinePlotConfig(
        id=plot_id,
        title="Line Graph",
        extra_series=[Series(pairs=[(1, 2)], name="Extra1"), Series(pairs=[(2, 3)], name="Extra2")],
    )
    plot = linegraph.plot({"Sample1": {0: 1, 1: 1}}, pconfig=pconfig)

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()

    assert len(report.plot_data[plot_id]["datasets"]) == 1
    assert len(report.plot_data[plot_id]["datasets"][0]["lines"]) == 3
    assert len(report.plot_data[plot_id]["datasets"][0]["lines"][0]["pairs"]) == 2
    assert len(report.plot_data[plot_id]["datasets"][0]["lines"][1]["pairs"]) == 1
    assert len(report.plot_data[plot_id]["datasets"][0]["lines"][2]["pairs"]) == 1
    assert report.plot_data[plot_id]["datasets"][0]["lines"][0]["name"] == "Sample1"
    assert report.plot_data[plot_id]["datasets"][0]["lines"][1]["name"] == "Extra1"
    assert report.plot_data[plot_id]["datasets"][0]["lines"][2]["name"] == "Extra2"


def test_extra_series_multiple_datasets_different_series():
    """Should zip series with the datasets"""
    plot_id = "my_plot"
    pconfig = LinePlotConfig(
        id=plot_id,
        title="Line Graph",
        extra_series=[[Series(pairs=[(1, 2)], name="Extra1")], [Series(pairs=[(2, 3)], name="Extra2")]],
    )
    datasets = [{"Sample1": {0: 1, 1: 1}}, {"Sample1": {0: 2, 1: 2}}]
    plot = linegraph.plot(datasets, pconfig=pconfig)

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()

    assert len(report.plot_data[plot_id]["datasets"]) == 2
    for ds in report.plot_data[plot_id]["datasets"]:
        assert len(ds["lines"]) == 2
        assert len(ds["lines"][0]["pairs"]) == 2
        assert len(ds["lines"][1]["pairs"]) == 1
        assert ds["lines"][0]["name"] == "Sample1"
    assert report.plot_data[plot_id]["datasets"][0]["lines"][1]["name"] == "Extra1"
    assert report.plot_data[plot_id]["datasets"][1]["lines"][1]["name"] == "Extra2"


def test_extra_series_multiple_datasets_multiple_series():
    """Should copy the extra series to all datasets"""
    plot_id = "my_plot"
    pconfig = LinePlotConfig(
        id=plot_id,
        title="Line Graph",
        extra_series=[Series(pairs=[(1, 2)], name="Extra1"), Series(pairs=[(2, 3)], name="Extra2")],
    )
    plot = linegraph.plot([{"Sample1": {0: 1, 1: 1}}, {"Sample1": {0: 2, 1: 2}}], pconfig=pconfig)

    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()

    assert len(report.plot_data[plot_id]["datasets"]) == 2
    for ds in report.plot_data[plot_id]["datasets"]:
        assert len(ds["lines"]) == 3
        assert len(ds["lines"][0]["pairs"]) == 2
        assert len(ds["lines"][1]["pairs"]) == 1
        assert len(ds["lines"][2]["pairs"]) == 1
        assert ds["lines"][0]["name"] == "Sample1"
        assert ds["lines"][1]["name"] == "Extra1"
        assert ds["lines"][2]["name"] == "Extra2"


def test_dash_styles():
    plot_id = "my_plot"
    pconfig = {
        "id": plot_id,
        "title": "Line Graph",
        "extra_series": [
            {"dash": "dash", "pairs": [(1, 1)]},
            {"dashStyle": "dash", "pairs": [(1, 1)]},
            {"dash": "ShortDash", "pairs": [(1, 1)]},
            {"dashStyle": "ShortDash", "pairs": [(1, 1)]},
        ],
    }
    data = {
        "Sample1": {0: 1, 1: 1},
    }
    with patch("logging.Logger.warning") as log:
        plot = linegraph.plot(data, pconfig=pconfig)
        warnings = [call.args[0] for call in log.mock_calls if call.args]
        assert "• 'dashStyle' field is deprecated. Please use 'dash' instead" in warnings
        assert "• 'ShortDash' is a deprecated dash style, use 'dash'" in warnings
    assert isinstance(plot, Plot)
    report.reset()
    plot.add_to_report()
    assert len(report.plot_data) == 1
    assert plot_id in report.plot_data
    assert len(report.plot_data[plot_id]["datasets"][0]["lines"]) == 5
    for line in report.plot_data[plot_id]["datasets"][0]["lines"][1:]:
        assert line["dash"] == "dash"
