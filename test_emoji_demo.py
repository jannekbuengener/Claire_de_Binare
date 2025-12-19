#!/usr/bin/env python3
"""
Demo file to test the emoji filter system in action
This will trigger various emoji detection scenarios
"""

def process_user_data():
    # ✅ This comment emoji should be whitelisted
    user_name = "John Doe"
    
    # 🚀 This emoji in comment should trigger warning
    status_message = "Welcome! 🌟 Enjoy your stay!"  # Emoji in string
    
    # Very problematic: emoji in variable name
    user_😀_count = 42
    
    # Function with emoji (critical violation)
    def send_📧_notification():
        return "Email sent successfully! 🎉"
    
    return user_name

def calculate_metrics():
    # 🔥 Performance critical section
    total = 0
    for i in range(1000):
        total += i
    
    # Dashboard message with emojis
    dashboard_msg = "📊 Analytics: Revenue up 📈 15%"
    
    return {"total": total, "message": dashboard_msg}

class UserManager:
    """Manages user operations with emoji issues"""
    
    def __init__(self):
        self.welcome_msg = "👋 Welcome to our platform!"
        # ❌ This should trigger an error
        self.error_msg = "Something went wrong"
    
    def create_user(self, name):
        # 💡 Tip: Always validate user input
        if not name:
            return None
        return f"Created user: {name} 🎊"

# Test various emoji contexts
TEST_EMOJIS = {
    "success": "✅",
    "warning": "⚠️", 
    "fire": "🔥",
    "rocket": "🚀",
    "star": "🌟"
}

if __name__ == "__main__":
    print("Testing emoji filter system! 🧪")
    manager = UserManager()
    result = process_user_data()
    metrics = calculate_metrics()
    print("Demo complete! 🏁")