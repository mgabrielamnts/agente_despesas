import pandas as pd
from src.insights import detect_anomalies, monthly_insights

def test_monthly_total_and_previous_comparison():
    df=pd.DataFrame({"valor":[100.,50.,80.],"categoria":["Mercado","Lazer","Mercado"],"data":pd.to_datetime(["2026-10-01","2026-10-10","2026-09-15"])})
    result=monthly_insights(df,2026,10); assert result["total"]==150.; assert result["previous_total"]==80.; assert result["top_category"]=="Mercado"

def test_detects_high_outlier():
    df=pd.DataFrame({"valor":[20,21,19,20,200],"categoria":["Alimentação"]*5,"data":pd.to_datetime(["2026-10-01"]*5)})
    result=detect_anomalies(df); assert len(result)==1; assert result.iloc[0]["valor"]==200
