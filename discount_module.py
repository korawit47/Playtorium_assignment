class DiscountDetail:
    def __init__(self, name, amount):
        self.name = name
        self.amount = amount
    
    def __str__(self):
        return f"(Source={self.name}, Value={self.amount:.2f})"

class ShoppingItem:
    def __init__(self, name, price, quantity, category):
        self.name = name
        self.price = price
        self.quantity = quantity
        self.category = category
        self.total_initial_price = price * quantity
        self.discount_records: list[DiscountDetail] = []
    
    def calculate_current_discount(self):
        return sum([d.amount for d in self.discount_records])
    
    def get_net_price(self):
        return self.total_initial_price - self.calculate_current_discount()

    def __str__(self):
        return (f"Item(name={self.name}, initial_price={self.total_initial_price:.2f}, "
                f"category={self.category}, Net Price={self.get_net_price():.2f}, "
                f"Discounts={[str(d) for d in self.discount_records]})")

class BaseDiscountStrategy:
    def __init__(self, code, name):
        self.code = code
        self.name = name

    def distribute_discount(self, cart: list[ShoppingItem], total_discount_amount: float, total_base_price: float):
        if total_base_price == 0 or total_discount_amount <= 0:
            return cart, 0

        actual_discount_used = 0
        remaining_discount_to_distribute = total_discount_amount

        for item in cart:
            item_price = item.total_initial_price
            discount_to_apply = (item_price / total_base_price) * remaining_discount_to_distribute
            max_item_discount = item_price - item.calculate_current_discount()
            discount = min(discount_to_apply, max_item_discount)
            discount = max(0, discount) 
            item.discount_records.append(DiscountDetail(self.name, discount))
            actual_discount_used += discount
        return cart, actual_discount_used

class FixedCoupon(BaseDiscountStrategy):
    def __init__(self, code, amount):
        super().__init__(code, f"FixedCoupon({amount} Baht)")
        self.amount = amount

    def apply_to_cart(self, cart: list[ShoppingItem], total_base_price: float):
        return self.distribute_discount(cart, self.amount, total_base_price)

class PercentCoupon(BaseDiscountStrategy):
    def __init__(self, code, percentage):
        super().__init__(code, f"PercentCoupon({percentage}%)")
        self.percentage = percentage

    def apply_to_cart(self, cart: list[ShoppingItem], total_base_price: float):
        discount_pool = total_base_price * (self.percentage / 100)
        return self.distribute_discount(cart, discount_pool, total_base_price)

class SeasonalCampaign(BaseDiscountStrategy):
    def __init__(self, code, every_amount, discount):
        super().__init__(code, f"Seasonal(Every {every_amount} Get {discount})")
        self.every_amount = every_amount
        self.discount = discount
    
    def apply_to_cart(self, cart: list[ShoppingItem], total_base_price: float):
        total_discount_pool = (total_base_price // self.every_amount) * self.discount
        return self.distribute_discount(cart, total_discount_pool, total_base_price)

class CategoryOnTop:
    def __init__(self, code, category, percentage):
        self.name = f"CategoryOnTop({category},{percentage}%)"
        self.category = category
        self.percentage = percentage
    
    def apply_to_cart(self, cart: list[ShoppingItem], total_base_price: float):
        total_discount_used = 0
        for item in cart:
            if item.category == self.category:
                price_remaining = item.get_net_price()
                
                discount = price_remaining * (self.percentage / 100)
                discount = min(discount, price_remaining) 
                discount = max(0, discount)
                
                item.discount_records.append(DiscountDetail(self.name, discount))
                total_discount_used += discount
        return cart, total_discount_used

class PointOnTop:
    MAX_CAP_PERCENT = 20
    
    def __init__(self, code, points):
        self.name = f"PointOnTop({points} points)"
        self.points = points

    def apply_to_cart(self, cart: list[ShoppingItem], total_base_price: float):
        current_total_discount = sum([item.calculate_current_discount() for item in cart])
        max_cap_value = total_base_price * (self.MAX_CAP_PERCENT / 100)
        remaining_cap = max_cap_value - current_total_discount
        discount_pool = min(self.points, remaining_cap)
        discount_pool = max(0, discount_pool)

        subtotal_remaining = sum(item.get_net_price() for item in cart)
        total_discount_used = 0

        if discount_pool <= 0 or subtotal_remaining <= 0:
            return cart, 0
        
        for item in cart:
            item_price_remaining = item.get_net_price()
            
            discount_to_apply = (item_price_remaining / subtotal_remaining) * discount_pool
            
            discount = min(discount_to_apply, item_price_remaining)
            discount = max(0, discount)
            
            item.discount_records.append(DiscountDetail(self.name, discount))
            total_discount_used += discount

        return cart, total_discount_used

class DiscountProcessor:
    def __init__(self):
        pass

    def _select_best_coupon(self, total_base_price: float, coupon_candidates: list[BaseDiscountStrategy]):
        best_coupon = None
        max_discount = -1

        for coupon in coupon_candidates:
            discount_value = 0
            
            if isinstance(coupon, FixedCoupon):
                discount_value = coupon.amount
            elif isinstance(coupon, PercentCoupon):
                discount_value = total_base_price * (coupon.percentage / 100)
            
            if discount_value > max_discount:
                max_discount = discount_value
                best_coupon = coupon
        
        return best_coupon

    def calculate_final_price(self, cart: list[ShoppingItem], raw_campaign_list: list):
        coupon_candidates = []
        on_top_discount = None
        seasonal_discount = None
        
        for campaign in raw_campaign_list:
            camp_type = campaign.get('type')
            
            if camp_type == 'fixed_amount':
                coupon_candidates.append(FixedCoupon(campaign['code'], campaign['amount']))
            elif camp_type == 'percentage_discount':
                coupon_candidates.append(PercentCoupon(campaign['code'], campaign['percentage']))
            
            elif camp_type == 'percentage_category_on_top':
                if on_top_discount: return None, None, "Only one On Top campaign is allowed"
                on_top_discount = CategoryOnTop(campaign['code'], campaign['item_category'], campaign['percentage'])
            elif camp_type == 'point_discount_on_top':
                if on_top_discount: return None, None, "Only one On Top campaign is allowed"
                on_top_discount = PointOnTop(campaign['code'], campaign['points'])
            
            elif camp_type == 'seasonal':
                if seasonal_discount: return None, None, "Only one Seasonal campaign is allowed"
                seasonal_discount = SeasonalCampaign(campaign['code'], campaign['every_amount'], campaign['discount'])
            else: 
                return None, None, f"Unknown campaign type: {camp_type}"
            
        total_base_price = sum(item.total_initial_price for item in cart)
        
        best_coupon = self._select_best_coupon(total_base_price, coupon_candidates)

        if best_coupon:
            cart, _ = best_coupon.apply_to_cart(cart, total_base_price)

        if on_top_discount:
            cart, _ = on_top_discount.apply_to_cart(cart, total_base_price) 

        if seasonal_discount:
            cart, _ = seasonal_discount.apply_to_cart(cart, total_base_price)

        final_total_price = sum(item.get_net_price() for item in cart)
        
        return cart, final_total_price, None