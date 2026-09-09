from app.services.reporting import profit_and_loss


def test_reporting_contract():
    assert len(profit_and_loss(None)) == 4
