def format_indian_currency(amount):
    """Convert number to Indian currency format with proper commas"""
    try:
        amount = str(amount).replace('\u20b9', '').replace(',', '').replace(';', '')
        
        amount = float(amount)
        
        def format_number(n):
            s = str(n)
            l = len(s)
            if l > 3:
                return format_number(s[:-3]) + ',' + s[-3:]
            return s
        
        formatted = format_number(int(amount))
        
        decimal_part = amount - int(amount)
        if decimal_part > 0:
            formatted += f"{decimal_part:.2f}".replace('0.', '.')
            
        return f"\u20b9{formatted}"
    except ValueError:
        return amount

def format_percentage(value):
    """Format percentage values consistently"""
    try:
        value = str(value).replace('%', '')
        return f"{float(value):.1f}%"
    except ValueError:
        return value
