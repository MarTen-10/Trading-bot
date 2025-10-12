def classify(spy_row, vix_row, bull_vix_lt=18, bear_vix_gt=22):
    bull = (spy_row['EMA_S'] > spy_row['EMA_L']) and (vix_row['Close'] < bull_vix_lt)
    bear = (spy_row['EMA_S'] < spy_row['EMA_L']) and (vix_row['Close'] > bear_vix_gt)
    if bull: return +1
    if bear: return -1
    return 0
