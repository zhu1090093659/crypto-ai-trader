"""
提示词构建模块
包含所有与AI提示词生成相关的格式化和构建函数
"""

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

# ==================== 基础格式化函数 ====================


def format_number(value, decimals: int = 2) -> str:
    """格式化数字，自动处理整数和小数"""
    if value is None:
        return "--"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(val - round(val)) < 1e-6:
        return str(int(round(val)))
    formatted = f"{val:.{decimals}f}"
    return formatted.rstrip("0").rstrip(".") if "." in formatted else formatted


def format_percentage(value: Optional[float]) -> str:
    """格式化百分比"""
    if value is None:
        return "--"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


def format_currency(value: Optional[float], decimals: int = 2) -> str:
    """格式化货币数值，值为空时返回 --"""
    if value is None:
        return "--"
    try:
        val = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"${val:,.{decimals}f}"


def format_sequence(values: List[float], indent: int = 2, per_line: int = 10, decimals: int = 2) -> str:
    """格式化数字序列为多行显示"""
    if not values:
        return " " * indent + "[]"
    parts = [format_number(v, decimals) for v in values]
    lines = []
    for i in range(0, len(parts), per_line):
        chunk = ", ".join(parts[i : i + per_line])
        lines.append(chunk)
    if not lines:
        return " " * indent + "[]"
    result_lines = []
    result_lines.append(" " * indent + "[" + lines[0] + ("," if len(lines) > 1 else "]"))
    for idx in range(1, len(lines)):
        suffix = "," if idx < len(lines) - 1 else "]"
        result_lines.append(" " * (indent + 1) + lines[idx] + suffix)
    return "\n".join(result_lines)


# ==================== 历史数据分析函数 ====================


def compute_accuracy_metrics(history: List[Dict]) -> Dict:
    """计算历史信号准确率指标"""
    evaluated = [rec for rec in history if rec.get("result") in ("success", "fail")]

    def summarize(records: List[Dict]) -> Dict:
        total = len(records)
        success = sum(1 for r in records if r.get("result") == "success")
        ratio = success / total if total else None
        return {"total": total, "success": success, "ratio": ratio}

    metrics = {
        "windows": {"10": summarize(evaluated[-10:]), "30": summarize(evaluated[-30:]), "50": summarize(evaluated[-50:])},
        "by_signal": {},
        "by_confidence": {},
        "by_leverage": {},
    }

    for signal_label in ["BUY", "SELL", "HOLD"]:
        metrics["by_signal"][signal_label] = summarize([r for r in evaluated if r.get("signal") == signal_label])

    for confidence in ["HIGH", "MEDIUM", "LOW"]:
        metrics["by_confidence"][confidence] = summarize([r for r in evaluated if r.get("confidence") == confidence])

    leverage_buckets = {"3-8x": lambda lev: 3 <= lev <= 8, "9-12x": lambda lev: 9 <= lev <= 12, "13-20x": lambda lev: 13 <= lev <= 20}
    for label, predicate in leverage_buckets.items():
        metrics["by_leverage"][label] = summarize(
            [r for r in evaluated if isinstance(r.get("leverage"), (int, float)) and predicate(int(r["leverage"]))]
        )
    return metrics


def format_ratio(summary: Dict) -> str:
    """格式化准确率比例"""
    total = summary.get("total", 0)
    success = summary.get("success", 0)
    ratio = summary.get("ratio")
    if not total:
        return "-- (--/0)"
    percent = f"{ratio * 100:.0f}%"
    return f"{percent} ({success}✓/{total})"


def format_history_table(history: List[Dict]) -> str:
    """格式化历史判断验证表格"""
    if not history:
        return "  无历史信号记录\n"
    last_records = history[-50:]
    total = len(last_records)
    lines = ["  序号 信号  信心 杠杆  入场价  验证价  涨跌    结果"]
    for idx, record in enumerate(last_records):
        seq_no = idx - total
        signal = (record.get("signal") or "--").upper().ljust(4)
        confidence = (record.get("confidence") or "--").upper().ljust(3)
        leverage = f"{int(record.get('leverage', 0)):>2}x" if record.get("leverage") is not None else "2x"
        entry = format_number(record.get("entry_price"))
        validation = format_number(record.get("validation_price"))
        change_pct = format_percentage(record.get("price_change_pct"))
        result_symbol = {"success": "✓", "fail": "✗"}.get(record.get("result"), "·")
        lines.append(f"  {seq_no:>3}  {signal} {confidence} {leverage:>4}  {entry:>7}  {validation:>7}  {change_pct:>6}   {result_symbol}")
    return "\n".join(lines)


def format_accuracy_summary(metrics: Dict) -> str:
    """格式化准确率统计摘要"""
    lines = ["  【准确率统计分析】", "", "  时间窗口:"]
    lines.append(f"  - 最近10次: {format_ratio(metrics['windows']['10'])}")
    lines.append(f"  - 最近30次: {format_ratio(metrics['windows']['30'])}")
    lines.append(f"  - 最近50次: {format_ratio(metrics['windows']['50'])}")
    lines.append("")
    lines.append("  按信号类型:")
    for signal_label in ["BUY", "SELL", "HOLD"]:
        lines.append(f"  - {signal_label:<4}: {format_ratio(metrics['by_signal'][signal_label])}")
    lines.append("")
    lines.append("  按信心等级:")
    for confidence in ["HIGH", "MEDIUM", "LOW"]:
        lines.append(f"  - {confidence:<6}: {format_ratio(metrics['by_confidence'][confidence])}")
    lines.append("")
    lines.append("  按杠杆范围:")
    for bucket in ["3-8x", "9-12x", "13-20x"]:
        lines.append(f"  - {bucket:<6}: {format_ratio(metrics['by_leverage'][bucket])}")
    lines.append("")
    lines.append("  关键观察:")
    lines.append("  - 高信心信号准确率显著优于低信心，应积极寻找HIGH机会")
    lines.append("  - 理想信心度分布: HIGH 25% | MEDIUM 50% | LOW 25%")
    lines.append("  - 不要过度保守！只在真正不确定时才用LOW")
    return "\n".join(lines)


# ==================== 仓位建议表格构建 ====================


def build_position_suggestion_table(position_suggestions: Dict[str, Dict], config: Dict, asset_name: str) -> str:
    """构建智能仓位建议表格"""
    lines = []
    leverage_min = config["leverage_min"]
    leverage_default = config["leverage_default"]
    leverage_max = config["leverage_max"]
    min_quantity = position_suggestions.get("min_quantity", config["amount"])
    min_contracts = position_suggestions.get("min_contracts", 0)

    def row(confidence_label: str, leverage: int) -> str:
        key = f"{confidence_label}_{leverage}"
        suggestion = position_suggestions.get(key, {})
        quantity = suggestion.get("quantity", 0)
        contracts = suggestion.get("contracts")
        value = suggestion.get("value", 0)
        margin = suggestion.get("margin", 0)
        meets_min = suggestion.get("meets_min", True)
        meets_margin = suggestion.get("meets_margin", True)
        status_parts = []
        status_parts.append("满足最小交易量" if meets_min else "低于最小交易量")
        status_parts.append("保证金充足" if meets_margin else "保证金不足")
        flag = "✅" if suggestion.get("meets", True) else "❌"
        status = " & ".join(status_parts)
        contracts_info = f"{contracts:.3f}张, " if contracts is not None else ""
        return f"  • {leverage}x: {quantity:.6f} {asset_name} ({contracts_info}价值 ${value:,.2f}), 需 {margin:.2f} USDT {flag} {status}"

    lines.append("  【智能仓位建议表】- 已为你精确计算")
    lines.append("")
    usable_margin = position_suggestions.get("usable_margin", position_suggestions.get("available_balance", 0) * 0.8)
    lines.append(
        f"  账户状态: 可用 {position_suggestions.get('available_balance', 0):.2f} USDT | 可用保证金 {usable_margin:.2f} USDT | 价格 ${position_suggestions.get('current_price', 0):,.2f} | 最小量 {min_quantity} {asset_name} ({min_contracts:.3f} 张)"
    )
    lines.append("")
    sections = [("HIGH", "高信心(HIGH) - 70%保证金"), ("MEDIUM", "中信心(MEDIUM) - 50%保证金"), ("LOW", "低信心(LOW) - 30%保证金")]
    for confidence_key, title in sections:
        lines.append(f"  {title}:")
        for lev in [leverage_min, leverage_default, leverage_max]:
            lines.append(row(confidence_key, lev))
        lines.append("")
    return "\n".join(lines)


# ==================== 交易历史表格构建 ====================


def format_trade_history_table(trade_history: List[Dict], max_rows: int = 20) -> str:
    """格式化实际交易历史表格"""
    if not trade_history:
        return "  暂无实际交易记录\n"

    lines = []
    lines.append("  序号 时间          操作类型      方向   价格      数量(ETH)  杠杆 信心  盈亏(USDT)")
    lines.append("  " + "-" * 85)

    recent_trades = trade_history[-max_rows:] if len(trade_history) > max_rows else trade_history

    for idx, trade in enumerate(recent_trades, start=1):
        seq = idx - len(recent_trades)  # 负数序号，-1表示最近一次
        timestamp = trade.get("timestamp", "")[:16]  # 只取日期和时分
        trade_type_display = trade.get("trade_type_display", "")[:12]  # 限制长度
        side = trade.get("side", "")
        side_display = "多" if side == "long" else "空" if side == "short" else "--"
        price = trade.get("price", 0)
        amount = trade.get("amount", 0)
        leverage = trade.get("leverage", 0)
        confidence = trade.get("confidence", "MED")[:3]
        pnl = trade.get("pnl", 0)

        lines.append(
            f"  {seq:>3}  {timestamp}  {trade_type_display:<12}  {side_display:<4}  {price:>8.2f}  {amount:>9.6f}  {leverage:>2}x  {confidence:<4}  {pnl:>+8.2f}"
        )

    return "\n".join(lines) + "\n"


def build_trade_frequency_warning(trade_history: List[Dict]) -> str:
    """分析交易频率并生成警告信息"""
    if not trade_history or len(trade_history) < 2:
        return ""

    warnings = []
    now = datetime.now()

    # 分析最近的交易
    recent_10 = trade_history[-10:] if len(trade_history) >= 10 else trade_history

    # 1. 检查最近一次交易的时间间隔
    last_trade = trade_history[-1]
    last_trade_time = datetime.strptime(last_trade["timestamp"], "%Y-%m-%d %H:%M:%S")
    minutes_since_last = (now - last_trade_time).total_seconds() / 60

    if minutes_since_last < 15:
        warnings.append(f"  警告：距离上次交易仅{minutes_since_last:.1f}分钟，请谨慎操作避免频繁交易！")

    # 2. 检查最近交易的频率
    if len(recent_10) >= 5:
        first_time = datetime.strptime(recent_10[0]["timestamp"], "%Y-%m-%d %H:%M:%S")
        last_time = datetime.strptime(recent_10[-1]["timestamp"], "%Y-%m-%d %H:%M:%S")
        time_span_hours = (last_time - first_time).total_seconds() / 3600

        if time_span_hours > 0:
            trades_per_hour = len(recent_10) / time_span_hours
            if trades_per_hour > 2:  # 每小时超过2次交易
                warnings.append(f"  提示：最近交易频率较高（{trades_per_hour:.1f}次/小时），建议降低交易频率提高质量")

    # 3. 检查来回反转模式（多->空->多 或 空->多->空）
    if len(recent_10) >= 4:
        # 检测是否存在短时间内的来回反转
        flip_flop_count = 0
        for i in range(2, len(recent_10)):
            side_a = recent_10[i - 2].get("side")
            side_b = recent_10[i - 1].get("side")
            side_c = recent_10[i].get("side")
            # 如果A和C相同，但B不同，说明来回反转了
            if side_a and side_b and side_c and side_a == side_c and side_b != side_a:
                flip_flop_count += 1

        if flip_flop_count >= 2:
            warnings.append(f"  提示：检测到{flip_flop_count}次来回反转（如：多→空→多），这种模式通常导致亏损")

    # 4. 计算最近交易的盈亏情况
    total_pnl = sum(t.get("pnl", 0) for t in recent_10 if "pnl" in t)
    profitable_trades = len([t for t in recent_10 if t.get("pnl", 0) > 0])

    if len(recent_10) >= 5:
        win_rate = profitable_trades / len(recent_10) * 100
        if total_pnl < 0:
            warnings.append(f"   分析：最近{len(recent_10)}笔交易累计亏损{abs(total_pnl):.2f} USDT（胜率{win_rate:.0f}%），建议提高信号质量")
        elif win_rate < 50:
            warnings.append(f"   分析：最近{len(recent_10)}笔交易胜率{win_rate:.0f}%，建议更谨慎选择交易时机")

    # 5. 添加交易建议
    if warnings:
        warnings.append("\n   建议策略：")
        warnings.append("     • 只在HIGH信心且多个指标共振时才交易")
        warnings.append("     • 避免在15-30分钟内重复开平仓")
        warnings.append("     • 使用HOLD信号耐心等待更好的机会")
        warnings.append("     • 减少低质量交易，宁可少赚也不多亏\n")

    return "\n".join(warnings) if warnings else ""


# ==================== 主提示词构建函数 ====================


def build_professional_prompt(
    ctx, symbol: str, price_data: Dict, config: Dict, position_suggestions: Dict[str, Dict], sentiment_text: str, current_position: Optional[Dict]
) -> str:
    """构建专业的交易分析提示词"""
    df: pd.DataFrame = price_data.get("full_data")  # type: ignore
    short_df = df.tail(20) if df is not None else None

    # 提取价格和技术指标序列
    prices = short_df["close"].tolist() if short_df is not None else []
    sma5 = short_df["sma_5"].tolist() if short_df is not None else []
    sma20 = short_df["sma_20"].tolist() if short_df is not None else []
    ema20 = short_df["ema_20"].tolist() if short_df is not None else []
    rsi = short_df["rsi"].tolist() if short_df is not None else []
    rsi_7 = short_df["rsi_7"].tolist() if short_df is not None else []
    macd = short_df["macd"].tolist() if short_df is not None else []
    volume = short_df["volume"].tolist() if short_df is not None else []

    # 获取历史记录和统计指标
    history = ctx.signal_history[symbol]
    metrics = compute_accuracy_metrics(history)
    history_table = format_history_table(history)
    accuracy_summary = format_accuracy_summary(metrics)

    # 获取实际交易历史
    trade_history = ctx.web_data["symbols"][symbol].get("trade_history", [])
    trade_history_table = format_trade_history_table(trade_history)

    # 系统运行状态
    runtime_minutes = int((datetime.now() - ctx.start_time).total_seconds() / 60)
    runtime_hours = runtime_minutes / 60
    ai_calls = ctx.metrics["ai_calls"]
    open_positions = sum(1 for pos in ctx.position_state.values() if pos)
    closed_trades = ctx.metrics["trades_closed"]

    asset_name = config["display"].split("-")[0]
    position_table = build_position_suggestion_table(position_suggestions, config, asset_name)

    # 当前持仓状态
    if current_position:
        position_status = f"{current_position.get('side', '--')} {current_position.get('size', 0)} {asset_name} @{format_number(current_position.get('entry_price'))}, 未实现盈亏: {format_number(current_position.get('unrealized_pnl'))} USDT"
    else:
        position_status = "无持仓"

    # 获取技术指标数据
    tech = price_data["technical_data"]
    levels = price_data.get("levels_analysis", {})

    # 获取资金费率和持仓量（如果有）
    # 注意：为避免循环导入，这些数据应该在price_data中提供或作为参数传入
    funding_rate_text = price_data.get("funding_rate_text", "暂无数据")
    open_interest_text = price_data.get("open_interest_text", "暂无数据")

    # 构建提示词各部分
    prompt_sections = [
        f"\n  你是加密货币交易分析师 | {config['display']} {config['timeframe']}周期\n",
        f"  【系统】运行{runtime_minutes}分钟({runtime_hours:.1f}h) | AI:{ai_calls} | 开:{ctx.metrics['trades_opened']} | 平:{closed_trades} | 持仓:{open_positions}\n",
        "  注：序列按 最旧→最新\n",
        "  重要：每个数组最后一个元素为最新数据点\n",
        "  【短期(20)】\n",
        "  价格(USDT):\n" + format_sequence(prices, decimals=2),
        "\n  VWMA5:\n" + format_sequence(sma5, decimals=2),
        "\n  VWMA20:\n" + format_sequence(sma20, decimals=2),
        "\n  VWEMA20:\n" + format_sequence(ema20, decimals=2),
        "\n  RSI14:\n" + format_sequence(rsi, decimals=2),
        "\n  RSI7:\n" + format_sequence(rsi_7, decimals=2),
        "\n  MACD:\n" + format_sequence(macd, decimals=2),
        "\n  量(" + asset_name + "):\n" + format_sequence(volume, decimals=2),
        "\n  【历史信号验证-近50】\n" + history_table + "\n",
        accuracy_summary + "\n",
        "  【实盘交易-近20】(与上述信号不同：此处为已执行)\n",
        trade_history_table,
        build_trade_frequency_warning(trade_history),
        "  【市场概览】\n",
        f"  价: ${price_data['price']:,} ({price_data.get('price_change', 0):+.2f}%)\n"
        f"  持仓: {position_status}\n"
        f"  情绪: {sentiment_text or '暂无数据'}\n",
        f"  资金费率: {funding_rate_text} | 持仓量: {open_interest_text}\n",
        "  【技术摘要】\n"
        f"  - 短期: {price_data['trend_analysis'].get('short_term', 'N/A')}\n"
        f"  - 中期: {price_data['trend_analysis'].get('medium_term', 'N/A')}\n"
        f"  - VWMA50: ${tech.get('sma_50', 0):.2f} (偏离: {((price_data['price'] - tech.get('sma_50', 0)) / tech.get('sma_50', 1) * 100):+.2f}%)\n"
        f"  - VWEMA20: ${tech.get('ema_20', 0):.2f} (偏离: {((price_data['price'] - tech.get('ema_20', 0)) / tech.get('ema_20', 1) * 100):+.2f}%)\n"
        f"  - VWEMA50: ${tech.get('ema_50', 0):.2f} (偏离: {((price_data['price'] - tech.get('ema_50', 0)) / tech.get('ema_50', 1) * 100):+.2f}%)\n"
        f"  - RSI(14): {tech.get('rsi', 0):.2f} | RSI(7): {tech.get('rsi_7', 0):.2f}\n"
        f"  - MACD: {tech.get('macd', 0):.4f} | 信号: {tech.get('macd_signal', 0):.4f} | 柱: {tech.get('macd_histogram', 0):.4f}\n"
        f"  - 布林: 上 ${tech.get('bb_upper', 0):.2f} | 下 ${tech.get('bb_lower', 0):.2f} | 位 {tech.get('bb_position', 0):.2%}\n"
        f"  - ATR: ${tech.get('atr', 0):.2f} | ATR(3): ${tech.get('atr_3', 0):.2f}\n"
        f"  - 量: {price_data.get('volume', 0):.2f} {asset_name} | 均量20: {tech.get('volume_ma', 0):.2f} | 比率: {tech.get('volume_ratio', 0):.2f}x\n"
        f"  - 位: 支撑 ${levels.get('static_support', 0):.2f} | 阻力 ${levels.get('static_resistance', 0):.2f}\n",
        position_table,
        "  【信心度】\n"
        "  - HIGH: 多指标强共振 + 放量 + 关键位突破/跌破\n"
        "  - MEDIUM: 2-3指标支持，方向明确但动能一般/待确认\n"
        "  - LOW: 指标分歧/震荡/量能不足（慎用）\n"
        "  【动作空间】\n"
        "  - BUY: 上涨信号占优（RSI上行、MACD金叉、上穿均线并放量等）\n"
        "  - SELL: 下跌信号占优（RSI下行、MACD死叉、跌破均线并放量等）——做空开仓\n"
        "  - CLOSE: 有持仓且出现反转/触及止盈止损/动能衰竭/情绪恶化\n"
        "  - HOLD: 方向不明或信号冲突\n"
        "  - 记：SELL是做空机会，不是平仓\n",
        "  【持仓约束】\n",
        "  - 不加仓：同一资产仅保留一个方向的持仓\n",
        "  - 不对冲：不可同时持有同一资产的多与空\n",
        "  - 不部分平仓：平仓需一次性全平\n",
        "  【头寸管理框架】\n",
        "  - 头寸(USDT) = 可用资金 × 杠杆 × 分配比例\n",
        "  - 数量(币) = 头寸(USDT) / 当前价格\n",
        f"  - 杠杆建议：LOW {config['leverage_min']}-{max(config['leverage_min'], 3)}x | MEDIUM 3-8x | HIGH 8-{config['leverage_max']}x（结合信心与波动）\n",
        "  - 集中度：单笔不应占用>40%可用资金\n",
        "  【决策规则】\n",
        "  1) 综合 技术 + 历史准确率 + 资金费率/持仓量\n"
        "  2) 积极找HIGH；MEDIUM为主；LOW尽量少\n"
        "  3) 多空均衡：明确下跌时应选择SELL\n"
        "  4) 持仓管理：必要时CLOSE而非被动止损\n"
        "  5) 频率：距上次<15分钟优先HOLD；频率高/胜率低→提高门槛\n"
        "  【下单数量】\n"
        f"  流程：确定confidence → 选{config['leverage_min']}/{config['leverage_default']}/{config['leverage_max']}x → 从建议表复制对应数量（6位小数，勿改）\n"
        "  - signal=CLOSE 时无需填写 leverage 与 order_quantity\n"
        "  【止盈止损】\n"
        "  - 依据ATR/支撑阻力/信心：止损2-8%，止盈4-15%，RR≥1:1.5\n"
        "  - CLOSE填0；HOLD写观察区间；避免过窄(<1%)\n"
        "  【移动止盈/止损】\n"
        "  - ts_active_px: 激活价；ts_callback_rate(%) 或 ts_callback_spread(价差)\n"
        "  - 建议结合ATR/入场价/止盈价给出\n",
        "  【回撤控制】\n",
        "  - 最大回撤：若账户净值较峰值回撤>15%，暂停交易（仅HOLD）\n",
        "  - 当日亏损：若当日亏损>5%，当天进入仅HOLD模式\n",
        "  【相关性与分散】\n",
        "  - 入场前检查与现有持仓的相关性（优先BTC基准相关）\n",
        "  - 高相关资产(>0.7)的持仓同时不超过2个；避免过度集中\n",
        "  【市场状态识别】\n",
        "  - 趋势：顺势策略（突破/回踩延续），适度放宽止损\n",
        "  - 震荡：均值回归策略（区间上下沿反向），收窄止损\n",
        "  - 高波动：缩小仓位与杠杆，提高入场门槛\n",
        "  【输出校验】\n",
        "  - 所有数值字段须为正数（HOLD可用占位）\n",
        "  - 多单：take_profit>入场价，stop_loss<入场价；空单相反\n",
        "  - 预期RR不低于2:1；每笔风险控制在账户1-3%以内\n",
        "  - HOLD时：order_quantity=0，建议leverage填默认或省略\n",
        "  请仅返回JSON：\n"
        "  {\n"
        '    "signal": "BUY|SELL|CLOSE|HOLD",\n'
        '    "reason": "20周期+历史准确率综合(≤50字)",\n'
        '    "stop_loss": 价格,\n'
        '    "take_profit": 价格,\n'
        '    "confidence": "HIGH|MEDIUM|LOW",\n'
        f"    \"leverage\": {config['leverage_min']}-{config['leverage_max']}（CLOSE可省略）,\n"
        '    "order_quantity": 建议表中对应数量（6位小数，CLOSE可省略）,\n'
        '    "ts_active_px": 可省略(HOLD/CLOSE),\n'
        '    "ts_callback_rate": %，与ts_callback_spread二选一,\n'
        '    "ts_callback_spread": 价差（可选）\n'
        "  }\n"
        "  ---",
    ]

    return "\n".join(prompt_sections)


# ==================== 系统提示词构建 ====================


def build_system_prompt(config: Dict) -> str:
    """构建系统提示词"""
    return f"""你是加密货币量化交易分析师，专注多周期与风险控制。你作为自主交易代理，运行于去中心化永续合约市场（24/7）。

【专长】
- 趋势：VWMA/VWEMA基于典型价
- 共振：RSI双周期、MACD、布林带、ATR
- 微观：成交量、资金费率、持仓量
- 风控：ATR动态止损、仓位管理

【任务】
分析 {config['display']} 的 {config['timeframe']} 周期并给出决策，仅输出规范JSON。

【信心定义】
- HIGH：多指标强共振+量能配合+关键位突破/跌破
- MEDIUM：2-3指标支持，方向明确但动能一般/待确认
- LOW：指标分歧或震荡

【信号含义】
- BUY：上涨信号占优
- SELL：下跌信号占优（做空开仓，不是平仓）
- CLOSE：持仓存在且出现反转/触及止盈止损/动能衰竭
- HOLD：信号冲突或无方向

【持仓约束】
- 不加仓：同一资产仅保留一个方向的持仓
- 不对冲：不可同时持有同一资产的多与空
- 不部分平仓：平仓需一次性全平

【回撤控制】
- 最大回撤：若账户净值较峰值回撤>15%，暂停交易（仅HOLD）
- 当日亏损：若当日亏损>5%，当天进入仅HOLD模式

【相关性与分散】
- 入场前检查与现有持仓的相关性（优先BTC基准相关）
- 高相关资产(>0.7)的持仓同时不超过2个；避免过度集中

【市场状态识别】
- 趋势：顺势策略（突破/回踩延续），适度放宽止损
- 震荡：均值回归策略（区间上下沿反向），收窄止损
- 高波动：缩小仓位与杠杆，提高入场门槛

【风险管理（强制）】
- 目标RR≥2:1；止损2-8%，止盈4-15%，结合ATR/关键位
- 单笔风险控制在账户1-3%以内，必要时优先CLOSE

【输出校验】
- 数值字段须为正数（HOLD可用占位）；多单TP>入场、SL<入场；空单相反
- 注意数据顺序：所有序列最旧→最新（最后一项为最新）

【执行原则】
- 历史准确率优先；积极寻找HIGH；MEDIUM为主；LOW慎用
- 多空均衡：明确下跌时应选择SELL
- 出现反转信号或接近目标优先CLOSE，主动控险"""
