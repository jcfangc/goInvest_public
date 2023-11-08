from config import __BASE_PATH__, DirectoryManager
from productType import stock as sk


class goInvest:
    @staticmethod
    def main() -> None:
        # 分析的请求名单
        requirement = DirectoryManager().directoty_manage()
        # 获取行数，shape函数返回值为元组(行数，列数)
        require_num = requirement.shape[0]

        # 遍历名单
        for sequence in range(0, require_num):
            match requirement.loc[sequence, "productType"]:
                case "stock":
                    stock = sk.Stock(requirement.loc[sequence], today_date=None)
                    stock.analyze_stock()


# 开始程序
goInvest.main()
