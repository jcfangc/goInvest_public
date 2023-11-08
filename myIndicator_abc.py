"""myIndicator_abc.py 扮演一个接口，写一些指标中共性功能"""

from abc import ABC, abstractmethod
from pandas import DataFrame
from utils import dataSource_picker as dp
from utils.enumeration_label import ProductType, IndicatorName
from config import __BASE_PATH__, do_logging
from typing import Optional

import json

import datetime as dt
import os

logger = do_logging()


class MyIndicator(ABC):
    """一个指标的抽象类"""

    def __init__(
        self,
        data_path: Optional[str],
        today_date: Optional[dt.date],
        product_code: str,
        product_type: ProductType,
        indicator_name: IndicatorName,
        product_df_dict: Optional[dict[str, DataFrame]],
    ) -> None:
        self.data_path = (
            data_path or f"{__BASE_PATH__}\\data\\{product_type.value}\\{product_code}"
        )
        self.today_date = today_date or dt.date.today()
        self.product_code = product_code
        self.product_type = product_type
        self.indicator_name = indicator_name
        self.product_df_dict = product_df_dict or dp.dataPicker.product_source_picker(
            product_code=product_code,
            today_date=today_date,
            product_type=product_type,
        )

    def _remove_redundant_files(self) -> None:
        """
        删除多余的文件，请在calculate_indicator()函数一开始调用\n
        """
        indicator_path = f"{self.data_path}\\indicator"
        for period_short in ["D", "W"]:
            # 删除过往重复数据
            for file_name in os.listdir(indicator_path):
                # 防止stock_code和k_period_short为None时参与比较
                if self.product_code is not None:
                    # 指定K线过去的数据会被删除
                    if (
                        self.product_code and period_short and self.indicator_name.value
                    ) in file_name and self.today_date.strftime(
                        "%m%d"
                    ) not in file_name:
                        # 取得文件绝对路径
                        absfile_path = os.path.join(indicator_path, file_name)
                        logger.debug(f"删除冗余文件\n>>>>{file_name}")
                        # os.remove只能处理绝对路径
                        os.remove(absfile_path)

    @abstractmethod
    def calculate_indicator(self) -> dict[str, DataFrame]:
        """
        重写本函数末尾可以调用save_indicator()函数，自动将计算好的指标数据保存到csv文件
        """
        pass

    @abstractmethod
    def analyze(self) -> list[DataFrame]:
        """
        本函数重写时，一开始记得调用pre_analyze()函数，获取指标数据\n
        本函数重写时，在策略函数末尾可以调用save_strategy()函数，保存分析结果
        """
        pass

    def save_indicator(
        self, df_dict: dict[str, DataFrame], indicator_value_config_dict: Optional[dict]
    ) -> None:
        """
        保存指标，可以在calculate_indicator()函数最后调用，自动将计算好的指标数据保存到csv文件
        """
        for period in df_dict.keys():
            # 检查是否存在nan值
            if df_dict[period].isnull().values.any():
                # 填充nan值
                df_dict[period].fillna(value=0.0, inplace=True)
            # 输出字典到csv文件
            with open(
                file=f"{self.data_path}\\indicator\\{self.product_code}{period[0].upper()}_{self.today_date.strftime('%Y%m%d')}_{self.indicator_name.value}.csv",
                mode="w",
                encoding="utf-8",
            ) as f:
                df_dict[period].to_csv(f, index=True, encoding="utf-8")

        if indicator_value_config_dict is not None:
            # 将指标配置写入配置文件
            self.write_to_config(
                indicator_config_dict=self.make_indicator_config_dict(
                    **indicator_value_config_dict
                ),
                strategy_config_dict=None,
            )

    def get_dict(self) -> dict[str, DataFrame]:
        """
        一些机械的重复性工作，在analyze()函数内部，先调用本函数，获取指标数据
        """
        return_dict = dp.dataPicker.indicator_source_picker(
            product_code=self.product_code,
            today_date=self.today_date,
            product_type=self.product_type,
            indicator_name=self.indicator_name,
            product_df_dict=self.product_df_dict,
        )

        if any(df.empty for df in return_dict.values()):
            raise ValueError("技术指标数据为空！")

        return return_dict

    def save_strategy(
        self,
        df_judge: DataFrame,
        func_name: str,
        strategy_config_value_dict: Optional[dict],
    ) -> None:
        """
        输出df_sma_judge为csv文件，在strategy文件夹中\n
        在analyze()函数所调用的具体策略函数末尾，可以调用save_strategy()函数，保存分析结果
        """
        with open(
            f"{self.data_path}\\strategy\\{self.product_code}_{self.indicator_name.value}{func_name}_anlysis.csv",
            "w",
            encoding="utf-8",
        ) as f:
            df_judge.to_csv(f)
            logger.debug(
                f"查看{self.product_code}的'{self.indicator_name.value}{func_name}'分析结果\n>>>>{f.name}\n"
            )

        if strategy_config_value_dict is not None:
            # 将策略配置写入配置文件
            self.write_to_config(
                indicator_config_dict=None,
                strategy_config_dict=self.make_strategy_config_dict(
                    strategy_name=func_name, **strategy_config_value_dict
                ),
            )

    def make_indicator_config_dict(self, **kwargs) -> dict:
        """创建指标配置字典"""
        # 创建字典
        indicator_config_dict = {}

        # 将参数写入字典
        for key, value in kwargs.items():
            indicator_config_dict[key] = value
        return indicator_config_dict

    def make_strategy_config_dict(self, strategy_name: str, **kwargs) -> dict:
        """创建策略配置字典"""
        # 创建字典
        strategy_config_dict = {}
        # 写入策略名称
        strategy_config_dict["strategy_name"] = strategy_name
        # 将参数写入字典
        for key, value in kwargs.items():
            strategy_config_dict[key] = value
        return strategy_config_dict

    def write_to_config(
        self,
        indicator_config_dict: Optional[dict],
        strategy_config_dict: Optional[dict],
    ):
        """将数据写入配置文件"""
        config_path = f"{__BASE_PATH__}\\config.json"
        # 读取配置文件
        with open(config_path, "r") as f:
            config_data = json.load(f)
        # 查找键"ValueInCalculation"
        if "ValueInCalculation" not in config_data.keys():
            raise KeyError("键'ValueInCalculation'不存在！")
        else:
            if indicator_config_dict is not None:
                # 将指标配置写入字典
                config_data["ValueInCalculation"][
                    f"{self.indicator_name.value}"
                ] = indicator_config_dict
            if strategy_config_dict is not None:
                # 将策略配置写入字典
                config_data["ValueInCalculation"][f"{self.indicator_name.value}"][
                    f"{strategy_config_dict['strategy_name']}"
                ] = strategy_config_dict

        # 保存回文件
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=4)

    def read_from_config(self, strategy_name: Optional[str]):
        """从配置文件中读取数据"""
        config_path = f"{__BASE_PATH__}\\config.json"
        # 读取配置文件
        with open(config_path, "r") as f:
            config_data = json.load(f)
        # 查找键"ValueInCalculation"
        if "ValueInCalculation" not in config_data.keys():
            raise KeyError("键'ValueInCalculation'不存在！")
        else:
            if strategy_name is None:
                try:
                    return config_data["ValueInCalculation"][
                        f"{self.indicator_name.value}"
                    ]
                except KeyError:
                    return None
            else:
                try:
                    strategy_data = config_data["ValueInCalculation"][
                        f"{self.indicator_name.value}"
                    ][f"{strategy_name}"]
                    # 删除策略名称
                    del strategy_data["strategy_name"]

                    return strategy_data
                except KeyError:
                    return None
