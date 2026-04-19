def calculate_option_charges(
    buy_price,
    sell_price,
    lot_size,
    quantity=1,
    brokerage_per_order=0.0,  # OPTIONAL — set to 0 if no brokerage
    include_brokerage=True
):
    """
    Calculates NSE options trading taxes and charges.
    
    buy_price: option premium buy price
    sell_price: option premium sell price
    lot_size: contract lot size
    quantity: number of lots
    brokerage_per_order: flat brokerage per executed order
    include_brokerage: set False to disable brokerage cost
    """
    
    # Turnover calculations
    buy_turnover = buy_price * lot_size * quantity
    sell_turnover = sell_price * lot_size * quantity
    total_turnover = buy_turnover + sell_turnover

    # CONDITIONS & RATES (editable)
    EXCHANGE_RATE = 0.0003503    # 0.03503%
    STT_SELL_RATE = 0.001        # 0.10%
    SEBI_RATE = 0.000001         # 0.0001%
    STAMP_DUTY_RATE = 0.0005     # 0.05%
    GST_RATE = 0.18              # 18%
    
    # Brokerage (optional)
    brokerage = 0
    if include_brokerage:
        brokerage = brokerage_per_order * 2  # buy + sell
    
    # Charges calculation
    exchange_charges = total_turnover * EXCHANGE_RATE
    stt = sell_turnover * STT_SELL_RATE
    sebi_fees = total_turnover * SEBI_RATE
    stamp_duty = buy_turnover * STAMP_DUTY_RATE
    gst = GST_RATE * (brokerage + exchange_charges + sebi_fees)
    
    # Total charges
    total_charges = brokerage + exchange_charges + stt + sebi_fees + stamp_duty + gst
    
    # Net profit calculation
    gross_profit = (sell_price - buy_price) * lot_size * quantity
    net_profit = gross_profit - total_charges
    
    return {
        "buy_turnover": buy_turnover,
        "sell_turnover": sell_turnover,
        "brokerage": brokerage,
        "exchange_charges": exchange_charges,
        "stt": stt,
        "sebi_fees": sebi_fees,
        "stamp_duty": stamp_duty,
        "gst": gst,
        "total_charges": total_charges,
        "gross_profit": gross_profit,
        "net_profit": net_profit
    }


# ---------------------------------------
# SAMPLE USAGE
# ---------------------------------------

result = calculate_option_charges(
    buy_price=50,
    sell_price=70,
    lot_size=50,
    quantity=2,
    brokerage_per_order=20,
    include_brokerage=True
)

# for k, v in result.items():
#     print(f"{k}: {v:.2f}")
