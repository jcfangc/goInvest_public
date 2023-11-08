"""mySRLine.py"""

if __name__ == "__main__":
    import sys
    import os

    # 将上级目录加入sys.path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))


import datetime as dt
import numpy as np
import matplotlib.dates as mdates
import pandas as pd

from pandas import DataFrame, Series
from utils.data_functionalizer import DataFunctionalizer as dfunc
from utils.myIndicator_abc import MyIndicator
from utils.enumeration_label import ProductType, IndicatorName
from matplotlib import pyplot as plt
from typing import Optional

# 本指标的参数
params = {}


class MySRLine(MyIndicator):
    def __init__(
        self,
        data_path: Optional[str],
        today_date: Optional[dt.date],
        product_code: str,
        product_type: ProductType,
        product_df_dict: Optional[dict[str, DataFrame]],
    ) -> None:
        params["today_date"] = today_date
        params["product_code"] = product_code
        params["product_type"] = product_type
        params["product_df_dict"] = product_df_dict
        super().__init__(
            data_path=data_path, indicator_name=IndicatorName.SRLine, **params
        )

    def calculate_indicator(self) -> dict[str, DataFrame]:
        """
        本函数计算支撑/阻力线，返回一个字典，包含不同周期的支撑/阻力线数据
        """
        print(f"正在计算{self.product_code}支撑阻力线...")

        # 清理重复文件
        super()._remove_redundant_files()

        # 本指标的参数
        default_indicator_config_value = {"threshold": 0.05}
        indicator_config_value = (
            super().read_from_config(None) or default_indicator_config_value
        )

        # 定义一个字典
        df_srline_dict = {
            "daily": DataFrame(),
            "weekly": DataFrame(),
        }

        # 根据数据和计算支撑/阻力线
        for period in ["daily", "weekly"]:
            closing_price = self.product_df_dict[period]["收盘"]
            closing_price_x = np.array(
                [mdates.date2num(close_x) for close_x in closing_price.index]
            )

            # 对数据进行线性变换
            transed_data, coeff = dfunc.shearing_and_recover(closing_price)

            # 取transed_data的最大值和最小值
            threshold = indicator_config_value["threshold"]  # config
            # 拟合点数量
            fit_points_num = int(len(transed_data) * threshold)
            # 取点
            max_points = transed_data.nlargest(fit_points_num)
            min_points = transed_data.nsmallest(fit_points_num)

            # 将max_points和min_points所代表的Series转化为np数组，方便拟合
            max_points_y = np.array(max_points.values)
            max_points_x = np.array(
                [mdates.date2num(date) for date in max_points.index]
            )
            min_points_y = np.array(min_points.values)
            min_points_x = np.array(
                [mdates.date2num(date) for date in min_points.index]
            )

            # 拟合阻力线
            resistance_coeff = np.polyfit(max_points_x, max_points_y, deg=1)
            # 根据resistance_coeff计算出拟合的阻力线的y值
            resistance_y = np.polyval(resistance_coeff, closing_price_x)
            # 根据y值和max_points.index创建一个Series
            resistance_line_data = Series(index=closing_price.index, data=resistance_y)

            # 拟合支撑线
            support_coeff = np.polyfit(min_points_x, min_points_y, deg=1)
            # 根据support_coeff计算出拟合的支撑线的y值
            support_y = np.polyval(support_coeff, closing_price_x)
            # 根据y值和min_points.index创建一个Series
            support_line_data = Series(index=closing_price.index, data=support_y)

            # 阻力线逆变换
            original_resistance_line_data = dfunc.shearing_and_recover(
                resistance_line_data, coeff=coeff
            )
            # 支撑线逆变换
            original_support_line_data = dfunc.shearing_and_recover(
                support_line_data, coeff=coeff
            )

            # # 画出拟合的直线和原数据
            # plt.plot(closing_price.index, closing_price, label="Smoothed Data")
            # plt.plot(
            #     original_resistance_line_data.index,
            #     original_resistance_line_data,
            #     label="Resistance Line",
            # )
            # plt.plot(
            #     original_support_line_data.index,
            #     original_support_line_data,
            #     label="Support Line",
            # )
            # plt.legend()
            # plt.show()

            # 创建DataFrame
            df_srline_dict[period] = DataFrame(
                index=closing_price.index, columns=["支撑线", "阻力线"]
            )
            df_srline_dict[period]["支撑线"] = original_support_line_data
            df_srline_dict[period]["阻力线"] = original_resistance_line_data
            df_srline_dict[period].index.name = "日期"

        # 保存指标
        super().save_indicator(
            df_dict=df_srline_dict, indicator_value_config_dict=indicator_config_value
        )
        # 返回df_srline_dict
        return df_srline_dict

    def analyze(self) -> list[DataFrame]:
        dict_srline = super().get_dict()
        # 调用策略函数
        srline_area_judge = self._pressure_area_strategy(dict_srline)
        # 返回策略结果
        return [srline_area_judge]

    # 策略函数名请轻易不要修改！！！若修改，需要同时修改枚举类内的StrategyName！！！
    def _pressure_area_strategy(
        self,
        dict_srline: dict[str, DataFrame],
    ) -> DataFrame:
        """
        压力区策略，将压力线和支撑线之间划分20个压力区\n
        由支撑线向上数第一个分区为第一区，以此类推\n
        """

        # 策略参数
        default_strategy_config_value = {"area_num": 20}
        strategy_config_value = (
            super().read_from_config(MySRLine._pressure_area_strategy.__name__)
            or default_strategy_config_value
        )

        area_num = strategy_config_value["area_num"]  # config

        # 创建一个空的DataFrame
        # 第一列为“日期”索引，第二列（daily）第三列（weekly）为-1至1的SRLine判断值
        df_srline_judge = DataFrame(
            index=dict_srline["daily"].index, columns=["daily", "weekly"]
        )

        # 初始化判断值为0
        df_srline_judge["daily"] = 0
        df_srline_judge["weekly"] = 0

        for period in ["daily", "weekly"]:
            # 取相应的支撑线和阻力线数据
            support_line = dict_srline[period]["支撑线"]
            resistance_line = dict_srline[period]["阻力线"]
            # 计算每个压力区的宽度
            area_width = (resistance_line - support_line) / area_num
            # 取相应的收盘价数据
            closing_price = self.product_df_dict[period]["收盘"]

            # 用循环表示所有区域
            pressue_area_index_list = []
            for i in range(area_num):
                lower_bound = support_line + area_width * i
                upper_bound = support_line + area_width * (i + 1)
                # 使用布尔索引获取位于当前区域的索引
                area_indices = closing_price[
                    (closing_price < upper_bound) & (closing_price >= lower_bound)
                ].index
                # 将当前区域的索引添加到列表中
                pressue_area_index_list.append(area_indices)

            # 获取股票数据收盘价格和支撑/阻力线数据的交叉情况
            # 和阻力线交叉
            resistance_cross = dfunc.check_cross(resistance_line, closing_price)
            # 和支撑线交叉
            support_cross = dfunc.check_cross(support_line, closing_price)

            met_line = "undefined"
            step = float(1 / area_num * 2)
            # 根据日期遍历dataframe
            for date in closing_price.index:
                # 当日期属于支撑线交叉点时
                if date in support_cross.values:
                    met_line = "support"
                # 当日期属于阻力线交叉点时
                if date in resistance_cross.values:
                    met_line = "resistance"

                if met_line == "support":
                    # 在第一区时或支撑线下方，判断为1
                    if support_line[date] >= closing_price[date]:
                        df_srline_judge.loc[date, period] = 1
                        continue
                    # 若在支撑线下方之后每上升一个压力区，判断值减0.5
                    # 判断其压力区
                    for i in range(area_num):
                        if date in pressue_area_index_list[i]:
                            if i >= area_num // 2:
                                expect = 1 - (i + 1) * step
                            else:
                                expect = 1 - i * step

                            # print(expect)
                            df_srline_judge.loc[date, period] = round(expect, 1)
                            break

                if met_line == "resistance":
                    df_srline_judge.loc[date, period] = -1.0

        # 保存策略结果
        super().save_strategy(
            df_judge=df_srline_judge,
            func_name=MySRLine._pressure_area_strategy.__name__,
            strategy_config_value_dict=strategy_config_value,
        )
        return df_srline_judge


if __name__ == "__main__":
    # 调用函数
    MySRLine(None, dt.date.today(), "600418", ProductType.Stock, None).analyze()
