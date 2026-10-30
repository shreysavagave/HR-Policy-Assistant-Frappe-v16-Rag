(() => {
    // Prevent duplicate widgets during Desk navigation.
    if (window.hrPolicyChatInitialized) return;
    window.hrPolicyChatInitialized = true;

    function createChatWidget() {
        if (document.getElementById("hr-policy-chat-widget")) return;

        const widget = document.createElement("div");
        widget.id = "hr-policy-chat-widget";

        widget.innerHTML = `
            <button
                id="hr-policy-chat-toggle"
                class="hr-policy-chat-toggle"
                aria-label="Open HR Policy Assistant"
                aria-expanded="false"
            >
                <span>AI</span>
            </button>

            <section
                id="hr-policy-chat-panel"
                class="hr-policy-chat-panel"
                aria-label="HR Policy Assistant"
                aria-hidden="true"
                hidden
            >
                <header class="hr-policy-chat-header">
                    <div>
                        <strong>HR Policy Assistant</strong>
                        <small>Ask about company policies</small>
                    </div>
                    <button
                        id="hr-policy-chat-close"
                        class="hr-policy-chat-close"
                        aria-label="Close chat"
                    >&times;</button>
                </header>

                <div
                    id="hr-policy-chat-messages"
                    class="hr-policy-chat-messages"
                    aria-live="polite"
                >
                    <div class="hr-policy-chat-message assistant">
                        Hi! Ask me a question about HR policies.
                    </div>
                </div>

                <form id="hr-policy-chat-form" class="hr-policy-chat-form">
                    <input
                        id="hr-policy-chat-input"
                        type="text"
                        placeholder="Ask an HR question..."
                        autocomplete="off"
                        aria-label="Your question"
                        maxlength="500"
                        required
                    />
                    <button type="submit" aria-label="Send message">
                        Send
                    </button>
                </form>
            </section>
        `;

        document.body.appendChild(widget);

        const toggle = widget.querySelector("#hr-policy-chat-toggle");
        const panel = widget.querySelector("#hr-policy-chat-panel");
        const close = widget.querySelector("#hr-policy-chat-close");
        const form = widget.querySelector("#hr-policy-chat-form");
        const input = widget.querySelector("#hr-policy-chat-input");
        const sendBtn = form.querySelector("button[type='submit']");
        const messages = widget.querySelector("#hr-policy-chat-messages");

        function openChat() {
            panel.hidden = false;
            panel.setAttribute("aria-hidden", "false");
            toggle.setAttribute("aria-expanded", "true");
            input.focus();
        }

        function closeChat() {
            panel.hidden = true;
            panel.setAttribute("aria-hidden", "true");
            toggle.setAttribute("aria-expanded", "false");
            toggle.focus();
        }

        function addMessage(text, role) {
            const message = document.createElement("div");
            message.className = `hr-policy-chat-message ${role}`;

            // Use textContent to avoid injecting HTML from user or AI text.
            message.textContent = text;
            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;

            return message;
        }

        function setBusy(busy) {
            input.disabled = busy;
            sendBtn.disabled = busy;
            if (!busy) input.focus();
        }

        toggle.addEventListener("click", () => {
            if (panel.hidden) openChat();
            else closeChat();
        });

        close.addEventListener("click", closeChat);

        form.addEventListener("submit", async (event) => {
            event.preventDefault();

            const question = input.value.trim();
            if (!question) return;

            addMessage(question, "user");
            input.value = "";
            setBusy(true);

            const pending = addMessage("Thinking...", "assistant");

            try {
                const r = await frappe.call({
                    method: "hr_policy_assistant.api.ask",
                    args: { question },
                });

                const { answer, sources } = r.message || {};
                let text = answer || "Sorry, I could not find an answer.";

                if (sources && sources.length) {
                    text += "\n\nSources: " + sources.join(", ");
                }

                pending.textContent = text;
            } catch (e) {
                pending.textContent =
                    "Sorry, something went wrong. Please try again.";
            } finally {
                setBusy(false);
                messages.scrollTop = messages.scrollHeight;
            }
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", createChatWidget, {
            once: true
        });
    } else {
        createChatWidget();
    }
})();