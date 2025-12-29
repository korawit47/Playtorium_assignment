from discount_module import ShoppingItem, DiscountProcessor
import json

if __name__ == "__main__":
    try:
        with open("test.json", "r", encoding="utf-8") as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        print("Error: test.json file not found. Please ensure the JSON file is in the same directory.")
        exit()
    except json.JSONDecodeError:
        print("Error: Could not decode test.json. Check the JSON format.")
        exit()

    if not isinstance(test_cases, list):
        test_cases = [test_cases]
        
    for data in test_cases:
        cart = []
        processor = DiscountProcessor()
        
        for item in data.get("products", []):
            cart.append(ShoppingItem(
                item.get("product_name"), 
                item.get("cost"), 
                item.get("units"), 
                item.get("item_category")
            ))
        
        final_cart, final_price, err = processor.calculate_final_price(cart, data.get("promos", []))
        
        print("Test Case:", data.get("test_name", "N/A"))
        
        expected_total = data.get("final_expected_cost")
        
        if err is not None:
            print("Error:", err)
        else:
            print("Final Cart:")
            for item in final_cart:
                print(item)
            
            is_correct = False
            if expected_total is not None:
                is_correct = abs(final_price - expected_total) < 0.01 
            else:
                is_correct = True 

            print("Final Price:", final_price)
            print("Expected Price:", expected_total)
            print("Result:", "Correct" if is_correct else "Incorrect")
        print("\n" + "="*40 + "\n")