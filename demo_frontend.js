// Frontend demo with emoji violations for testing

class UserInterface {
    constructor() {
        // UI messages with emojis
        this.messages = {
            welcome: "Welcome! 👋 Nice to see you",
            success: "Success! ✅ Operation completed",
            error: "Error! ❌ Please try again",
            loading: "Loading... ⏳ Please wait"
        };
        
        // Emoji in property name (violation)
        this.user_😊_status = "active";
    }
    
    // Function with emoji (critical violation)  
    show_📱_notification(message) {
        console.log(`📢 Notification: ${message}`);
        return true;
    }
    
    renderDashboard() {
        // 🔥 Performance: This renders the main dashboard
        const icons = {
            home: "🏠",
            settings: "⚙️",
            profile: "👤",
            notifications: "🔔"
        };
        
        return `
            <div class="dashboard">
                <h1>Dashboard 📊</h1>
                <button>Save 💾</button>
                <button>Delete 🗑️</button>
            </div>
        `;
    }
    
    // Comment with multiple emojis
    // 🎯 TODO: Optimize this function for better performance 🚀
    processData(data) {
        // ⚠️ Warning: This processes sensitive data
        return data.map(item => ({
            ...item,
            processed: true,
            timestamp: new Date(),
            status: "✅ Completed"
        }));
    }
}

// Export with emoji (should be caught)
export const notify_🎉_success = () => {
    alert("🎊 Congratulations! 🎉");
};

// Arrow function with emoji
const send_💌_message = (recipient) => {
    return `💌 Message sent to ${recipient} 📤`;
};

console.log("Frontend module loaded! 🚀");