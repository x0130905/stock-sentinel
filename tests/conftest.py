from __future__ import annotations

import pandas as pd
import pytest

from stock_sentinel.providers.sample import SampleProvider


@pytest.fixture(scope="session")
def sample_frame() -> pd.DataFrame:
    return SampleProvider().fetch("TEST", "1y").frame
