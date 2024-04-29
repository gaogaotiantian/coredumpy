import coredumpy


def pytest_addoption(parser):
    parser.addoption(
        "--enable-coredumpy",
        action="store_true",
        help="Enable coredumpy plugin.",
    )

    parser.addoption(
        "--coredumpy-dir",
        action="store",
        default="./coredumpy",
        help="The directory to store the core dump files.",
    )


def _get_description(report):
    underscore_count = (70 - len(report.head_line) - 2) // 2
    headline = f"{'_' * underscore_count} {report.head_line} {'_' * underscore_count}"
    return '\n'.join([headline, report.longreprtext])


def pytest_exception_interact(node, call, report):
    if not node.config.getoption("--enable-coredumpy"):
        return

    import pytest  # type: ignore
    if isinstance(report, pytest.TestReport):
        try:
            tb = call.excinfo.tb
            while tb.tb_next:
                tb = tb.tb_next
            filename = coredumpy.dump(tb.tb_frame,
                                      description=_get_description(report),
                                      directory=node.config.getoption("--coredumpy-dir"))
            print(f'Your frame stack is dumped, open it with\n'
                  f'coredumpy load {filename}')
        except Exception:  # pragma: no cover
            print("Failed to dump the frame stack.")
