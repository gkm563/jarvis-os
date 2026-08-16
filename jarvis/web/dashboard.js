/* JARVIS OS Web Dashboard - Frontend Controller */

const API_BASE = window.location.origin;

let activePlanId = null;
let pollInterval = null;
let sidebarWaveAnim = null;
let sparklineAnims = [];

document.addEventListener("DOMContentLoaded", () => {
    // Set dynamic timestamps
    updateTimestamps();
    
    // Initialize stats sparkline charts
    initSparklines();
    
    // Initialize sidebar canvas wave
    initSidebarWave();
    
    // Poll for pending confirmation approvals (sensitive action gate)
    setInterval(fetchPendingApprovals, 2000);
});

function updateTimestamps() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const welcomeTime = document.getElementById("welcomeTime");
    if (welcomeTime) welcomeTime.innerText = timeStr;
}

// Add styled chat bubbles in history logs
function addMessage(author, text, isUser = false) {
    const chatHistory = document.getElementById("chatHistory");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${isUser ? 'user' : 'jarvis'}`;
    
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    let bodyContent = "";
    if (text.startsWith("<ul>") || text.includes("msg-plan-box")) {
        bodyContent = text; // preformatted HTML like checklist or execution plans
    } else {
        // Convert double linebreaks to paragraphs
        bodyContent = text.split("\n\n").map(p => `<p>${escapeHTML(p)}</p>`).join("");
    }
    
    msgDiv.innerHTML = `
        <div class="msg-avatar">${isUser ? '👤' : '🤖'}</div>
        <div class="msg-content-wrapper">
            <div class="msg-header">
                <span class="msg-author">${author}</span>
                <span class="msg-time">${timeStr}</span>
            </div>
            <div class="msg-body">${bodyContent}</div>
        </div>
    `;
    
    chatHistory.appendChild(msgDiv);
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, 
        tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
    );
}

// Submit Goal / Natural Language Intent
async function submitGoal(customPrompt = null) {
    const inputEl = document.getElementById("goalInput");
    const goal = customPrompt || inputEl.value.trim();
    if (!goal) return;

    // Append user input bubble to chat
    addMessage("You", goal, true);
    inputEl.value = "";

    // Insert an initial JARVIS thinking placeholder bubble
    const thinkingId = "think-" + Math.random().toString(36).substring(2, 9);
    const thinkingDiv = document.createElement("div");
    thinkingDiv.className = "message jarvis";
    thinkingDiv.id = thinkingId;
    thinkingDiv.innerHTML = `
        <div class="msg-avatar">🤖</div>
        <div class="msg-content-wrapper">
            <div class="msg-header">
                <span class="msg-author">JARVIS</span>
                <span class="msg-time">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div class="msg-body">
                <p class="processing-text">🤖 Thinking... Analyzing intent and building plan...</p>
            </div>
        </div>
    `;
    document.getElementById("chatHistory").appendChild(thinkingDiv);
    document.getElementById("chatHistory").scrollTop = document.getElementById("chatHistory").scrollHeight;

    try {
        const response = await fetch(`${API_BASE}/v1/intent`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_goal: goal, execute_immediately: true })
        });

        if (!response.ok) throw new Error("Failed to process intent");
        const data = await response.json();
        activePlanId = data.plan_id;

        // Replace the thinking bubble with the actual execution plan
        thinkingDiv.remove();
        
        let planHtml = `
            <p>I have generated a plan with <strong>${data.step_count} step(s)</strong> for your request:</p>
            <div class="msg-plan-box">
                <div class="msg-plan-title">🧠 Plan DAG: ${escapeHTML(goal.substring(0, 40))}</div>
                <div class="msg-plan-steps" id="plan-steps-${activePlanId}">
                    ${renderInitialPlanSteps(data.plan)}
                </div>
            </div>
        `;
        addMessage("JARVIS", planHtml);
        
        // Add activity entry
        addRecentActivity(goal);
        
        startPlanPolling(activePlanId);
    } catch (err) {
        thinkingDiv.remove();
        addMessage("JARVIS", `⚠️ Error executing goal: ${err.message}`);
    }
}

function renderInitialPlanSteps(plan) {
    return plan.steps.map(step => `
        <div class="msg-step-item pending" id="step-${step.step_id}">
            <span>${escapeHTML(step.description)}</span>
            <span class="step-badge">PENDING</span>
        </div>
    `).join("");
}

// Preset Execution Helper
function runPreset(prompt) {
    submitGoal(prompt);
}

// Poll Plan Execution Progress and update bubble steps
function startPlanPolling(planId) {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/v1/plan/${planId}`);
            if (!res.ok) {
                clearInterval(pollInterval);
                return;
            }

            const plan = await res.json();
            const container = document.getElementById(`plan-steps-${planId}`);
            
            if (container) {
                container.innerHTML = plan.steps.map(step => {
                    const statusClass = step.status ? step.status.toLowerCase() : "pending";
                    return `
                        <div class="msg-step-item ${statusClass}" id="step-${step.step_id}">
                            <span>${escapeHTML(step.description)}</span>
                            <strong class="step-badge">${step.status}</strong>
                        </div>
                    `;
                }).join("");
            }

            if (plan.status === "COMPLETED" || plan.status === "FAILED") {
                clearInterval(pollInterval);
                if (plan.status === "COMPLETED") {
                    addMessage("JARVIS", `✅ Task complete! Successfully executed all steps.`);
                } else {
                    addMessage("JARVIS", `❌ Task failed during execution. Please review local logs.`);
                }
            }
        } catch (err) {
            console.error("Polling error:", err);
            clearInterval(pollInterval);
        }
    }, 1000);
}

// Trigger Voice Microphone on Laptop locally
async function triggerVoiceMic() {
    const pill = document.getElementById("listeningPill");
    if (!pill) return;
    
    // Transition to listening state visually
    pill.className = "listening-pill listening";
    pill.innerText = "● LISTENING";
    
    // Visual indicators: speed up waves
    document.querySelectorAll(".orb-wave").forEach(w => w.style.animationDuration = "1s");
    
    addMessage("JARVIS", "🎙️ Listening... Please speak your command into your microphone.");

    try {
        const res = await fetch(`${API_BASE}/v1/trigger_mic`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to trigger mic");
        
        // Wait 10 seconds (standard timeout) before returning to ready state
        setTimeout(() => {
            pill.className = "listening-pill ready";
            pill.innerText = "● READY";
            document.querySelectorAll(".orb-wave").forEach((w, idx) => {
                w.style.animationDuration = idx === 0 ? "2.5s" : "1.25s";
            });
        }, 10000);
        
    } catch (err) {
        addMessage("JARVIS", `⚠️ Mic trigger error: ${err.message}`);
        pill.className = "listening-pill ready";
        pill.innerText = "● READY";
    }
}

// Check Pending Approvals (Sensitive Action Gate)
async function fetchPendingApprovals() {
    try {
        const res = await fetch(`${API_BASE}/v1/pending_approvals`);
        if (!res.ok) return;

        const approvals = await res.json();
        const tokens = Object.keys(approvals);

        if (tokens.length > 0) {
            const token = tokens[0];
            const item = approvals[token];
            showApprovalModal(token, item);
        } else {
            hideApprovalModal();
        }
    } catch (err) {
        console.error("Error fetching approvals:", err);
    }
}

function showApprovalModal(token, details) {
    const modal = document.getElementById("approvalModal");
    document.getElementById("modalActionDesc").innerText = `${details.description} (${details.agent_name}:${details.action_type})`;
    document.getElementById("approveBtn").onclick = () => approveToken(token);
    modal.classList.add("active");
}

function hideApprovalModal() {
    document.getElementById("approvalModal").classList.remove("active");
}

async function approveToken(token) {
    try {
        const res = await fetch(`${API_BASE}/v1/plan/${activePlanId || 'any'}/confirm`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ confirmation_token: token })
        });
        if (res.ok) {
            addMessage("JARVIS", `🔓 Action approved. Resuming execution flow.`);
            hideApprovalModal();
        }
    } catch (err) {
        addMessage("JARVIS", `⚠️ Failed to approve action: ${err.message}`);
    }
}

// Mock settings action
function showSettings() {
    addMessage("JARVIS", "⚙️ Settings window opened. Configure API Keys directly via the console or `.env` files.");
}

// Dynamically add a recent activity row
function addRecentActivity(goal) {
    const list = document.getElementById("activityList");
    if (!list) return;
    
    const item = document.createElement("div");
    item.className = "activity-item";
    item.innerHTML = `
        <div class="activity-icon">⚡</div>
        <div class="activity-details">
            <div class="activity-title">${escapeHTML(goal)}</div>
            <div class="activity-time">Just now</div>
        </div>
    `;
    list.insertBefore(item, list.firstChild);
    if (list.children.length > 4) {
        list.removeChild(list.lastChild);
    }
}

/* Canvas Sparkline & Sine Wave Animations */

function initSparklines() {
    const configs = [
        { id: "cpuSparkline", color: "#00f0ff", baseVal: 23, idVal: "cpuValue", unit: "%" },
        { id: "memSparkline", color: "#7000ff", baseVal: 42, idVal: "memValue", unit: "%" },
        { id: "diskSparkline", color: "#10b981", baseVal: 68, idVal: "diskValue", unit: "%" },
        { id: "netSparkline", color: "#38bdf8", baseVal: 156, idVal: "netValue", unit: " Mbps" }
    ];
    
    configs.forEach(cfg => {
        const canvas = document.getElementById(cfg.id);
        if (!canvas) return;
        
        const ctx = canvas.getContext("2d");
        const points = Array(15).fill(cfg.baseVal);
        
        const interval = setInterval(() => {
            // Fluctuate value
            const delta = (Math.random() - 0.5) * (cfg.baseVal > 100 ? 15 : 4);
            let newVal = Math.round(cfg.baseVal + delta);
            newVal = Math.max(cfg.baseVal > 100 ? 50 : 5, Math.min(cfg.baseVal > 100 ? 300 : 95, newVal));
            
            // Update labels
            const valEl = document.getElementById(cfg.idVal);
            if (valEl) valEl.innerText = newVal + cfg.unit;
            
            points.push(newVal);
            points.shift();
            
            // Draw sparkline path
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = cfg.color;
            ctx.lineWidth = 1.5;
            ctx.beginPath();
            
            const step = canvas.width / (points.length - 1);
            points.forEach((p, idx) => {
                const x = idx * step;
                // normalize range
                const y = canvas.height - 3 - ((p / (cfg.baseVal > 100 ? 300 : 100)) * (canvas.height - 6));
                if (idx === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            });
            ctx.stroke();
        }, 1200);
        
        sparklineAnims.push(interval);
    });
}

function initSidebarWave() {
    const canvas = document.getElementById("sidebarWave");
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    let offset = 0;
    
    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "rgba(0, 240, 255, 0.4)";
        ctx.lineWidth = 1.5;
        
        // Sine Wave 1
        ctx.beginPath();
        for (let x = 0; x < canvas.width; x++) {
            const y = canvas.height / 2 + Math.sin(x * 0.05 + offset) * 5;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
        
        // Sine Wave 2
        ctx.strokeStyle = "rgba(112, 0, 255, 0.3)";
        ctx.beginPath();
        for (let x = 0; x < canvas.width; x++) {
            const y = canvas.height / 2 + Math.cos(x * 0.04 - offset * 0.8) * 6;
            if (x === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
        
        offset += 0.05;
        sidebarWaveAnim = requestAnimationFrame(draw);
    }
    draw();
}
