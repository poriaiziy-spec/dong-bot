from typing import Any

def calculate_group_balances(members: list[dict], expenses: list[dict]) -> dict[str, Any]:
    """
    محاسبه دنگ‌ها، مبالغ پرداختی، سهم هر شخص و فرمول تسویه نهایی.
    
    خروجی شامل:
    - total_spent: کل مبلغ خرج شده در گروه
    - member_stats: وضعیت هر عضو (پرداختی، سهم، طلبکاری/بدهکاری)
    - settlements: لیست تراکنش‌های بهینه جهت تسویه حساب کامل (کی به کی چقدر بدهد)
    """
    total_spent = sum(exp["amount"] for exp in expenses)
    
    # نگاشت شناسه کاربر به اطلاعات کاربر
    users_by_id = {m["id"]: m for m in members}
    
    # مقدار اولیه برای تمام اعضا
    paid_map = {m["id"]: 0 for m in members}
    owed_map = {m["id"]: 0 for m in members}
    
    # تجمیع مبالغ پرداختی و سهم‌ها
    for exp in expenses:
        payer_id = exp["payer_id"]
        if payer_id in paid_map:
            paid_map[payer_id] += exp["amount"]
        else:
            paid_map[payer_id] = exp["amount"]
            
        for share in exp.get("shares", []):
            u_id = share["user_id"]
            if u_id in owed_map:
                owed_map[u_id] += share["share_amount"]
            else:
                owed_map[u_id] = share["share_amount"]
                
    member_stats = []
    # محاسبه تراز (Net Balance): مثبت = طلبکار، منفی = بدهکار
    net_balances: dict[int, int] = {}
    for uid in (set(paid_map.keys()) | set(owed_map.keys())):
        if uid not in users_by_id:
            users_by_id[uid] = {"id": uid, "full_name": "عضو سابق"}

    all_uids = list(users_by_id.keys())

    for uid in all_uids:
        u = users_by_id[uid]
        paid = paid_map.get(uid, 0)
        owed = owed_map.get(uid, 0)
        net = paid - owed
        net_balances[uid] = net
        
        member_stats.append({
            "user": u,
            "paid": paid,
            "owed": owed,
            "net": net
        })
        
    # الگوریتم کمینه‌سازی تراکنش‌های تسویه بدهی (Greedy Debt Settlement)
    debtors = []   # بدهکارها: کسانی که باید پول بدهند (net < 0)
    creditors = [] # طلبکارها: کسانی که باید پول بگیرند (net > 0)
    
    for uid, net in net_balances.items():
        if net < -0.5:
            debtors.append({"user": users_by_id.get(uid, {"id": uid, "full_name": "کاربر"}), "amount": -net})
        elif net > 0.5:
            creditors.append({"user": users_by_id.get(uid, {"id": uid, "full_name": "کاربر"}), "amount": net})
            
    settlements = []
    
    # مرتب‌سازی برای جفت‌سازی بهینه
    debtors.sort(key=lambda x: x["amount"], reverse=True)
    creditors.sort(key=lambda x: x["amount"], reverse=True)
    
    i = 0
    j = 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors[i]
        creditor = creditors[j]
        
        transfer_amount = min(debtor["amount"], creditor["amount"])
        
        if transfer_amount > 0:
            settlements.append({
                "from_user": debtor["user"],
                "to_user": creditor["user"],
                "amount": int(round(transfer_amount))
            })
            
        debtor["amount"] -= transfer_amount
        creditor["amount"] -= transfer_amount
        
        if debtor["amount"] < 0.5:
            i += 1
        if creditor["amount"] < 0.5:
            j += 1
            
    return {
        "total_spent": total_spent,
        "member_stats": member_stats,
        "settlements": settlements
    }
