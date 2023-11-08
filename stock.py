import datetime as dt


from utils import dataSource_picker as dsp
from utils import data_analyst as da
from pandas import Series
from utils.enumeration_label import ProductType
from utils.enumeration_label import IndicatorName
from pandas import DataFrame


class Stock:
    """
    这是一个stock对象，创建该对象请调用构造函数并传入A股股票代码
    """

    def __init__(self, requirement: Series, today_date: dt.date | None) -> None:
        self.stock_code = requirement["identityCode"]
        self.today_date = dt.date.today() if today_date is None else today_date

    # 获取指定产品的日K/周K
    def obtain_kline(self) -> None:
        # 获取数据
        dsp.dataPicker.product_source_picker(
            self.stock_code,
            today_date=self.today_date,
            product_type=ProductType.Stock,
        )

    # 分析指定产品的日K/周K，生成分析报告
    def analyze_stock(self) -> None:
        # 调用分析函数
        da.StockAnalyst(
            stock_code=self.stock_code,
            today_date=self.today_date,
        ).analyze()

    def get_sma(self) -> dict[str, DataFrame]:
        return dsp.dataPicker.indicator_source_picker(
            product_code=self.stock_code,
            today_date=self.today_date,
            product_type=ProductType.Stock,
            indicator_name=IndicatorName.SMA,
            product_df_dict=None,
        )

    def get_ema(self) -> dict[str, DataFrame]:
        return dsp.dataPicker.indicator_source_picker(
            product_code=self.stock_code,
            today_date=self.today_date,
            product_type=ProductType.Stock,
            indicator_name=IndicatorName.EMA,
            product_df_dict=None,
        )

    def get_boll(self) -> dict[str, DataFrame]:
        return dsp.dataPicker.indicator_source_picker(
            product_code=self.stock_code,
            today_date=self.today_date,
            product_type=ProductType.Stock,
            indicator_name=IndicatorName.Boll,
            product_df_dict=None,
        )

    def get_srline(self) -> dict[str, DataFrame]:
        return dsp.dataPicker.indicator_source_picker(
            product_code=self.stock_code,
            today_date=self.today_date,
            product_type=ProductType.Stock,
            indicator_name=IndicatorName.SRLine,
            product_df_dict=None,
        )

    def get_rsi(self) -> dict[str, DataFrame]:
        return dsp.dataPicker.indicator_source_picker(
            product_code=self.stock_code,
            today_date=self.today_date,
            product_type=ProductType.Stock,
            indicator_name=IndicatorName.RSI,
            product_df_dict=None,
        )
