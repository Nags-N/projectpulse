import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

export default function Sidebar({ projectId, userId, collapsed, onToggle }) {
  const location = useLocation();

  const navItems = [
    {
      group: "INTELLIGENCE",
      items: [
        {
          label: "Manager Command",
          icon: "📊",
          path: "/manager",
          link: `/manager?project_id=${encodeURIComponent(projectId)}`,
          badge: null,
        },
        {
          label: "Tasks Command",
          icon: "⚡",
          path: "/tasks",
          link: `/tasks?project_id=${encodeURIComponent(projectId)}`,
          badge: null,
        },
        {
          label: "AI Copilot",
          icon: "✦",
          path: "/assistant",
          link: `/assistant?project_id=${encodeURIComponent(projectId)}`,
          badge: "AI",
        },
      ],
    },
    {
      group: "ENGINEERING REALITY",
      items: [
        {
          label: "Developer Telemetry",
          icon: "💻",
          path: "/developer",
          link: `/developer?project_id=${encodeURIComponent(projectId)}&user_id=${encodeURIComponent(userId || "DEV-001")}`,
          badge: null,
        },
        {
          label: "Testing Gates",
          icon: "🧪",
          path: "/tester",
          link: `/tester?project_id=${encodeURIComponent(projectId)}`,
          badge: null,
        },
        {
          label: "QA & Blockers",
          icon: "🛡️",
          path: "/qa",
          link: `/qa?project_id=${encodeURIComponent(projectId)}`,
          badge: null,
        },
      ],
    },
    {
      group: "OBSERVATORY FLEET",
      items: [
        {
          label: "PM Integrations",
          icon: "🔗",
          path: "/integrations",
          link: `/integrations?project_id=${encodeURIComponent(projectId)}`,
          badge: "Jira",
        },
        {
          label: "Connected Agents",
          icon: "🤖",
          path: "/agents",
          link: `/agents?project_id=${encodeURIComponent(projectId)}`,
          badge: null,
        },
      ],
    },
  ];

  return (
    <aside className={`app-sidebar ${collapsed ? "app-sidebar--collapsed" : ""}`}>
      {/* Brand Header */}
      <div className="sidebar-header">
        <Link to={`/manager?project_id=${encodeURIComponent(projectId)}`} className="sidebar-brand">
          <div className="brand-icon-wrap">
            <div className="brand-pulse-dot" />
          </div>
          {!collapsed && <span>ProjectPulse AI</span>}
        </Link>
        <button
          type="button"
          className="sidebar-toggle-btn"
          onClick={onToggle}
          title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {collapsed ? "»" : "«"}
        </button>
      </div>

      {/* Navigation Groups */}
      <nav className="sidebar-nav">
        {navItems.map((group, gIdx) => (
          <div key={gIdx} style={{ marginBottom: "0.25rem" }}>
            {!collapsed && <div className="sidebar-group-title">{group.group}</div>}
            {group.items.map((item) => {
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.link}
                  className={`sidebar-link ${isActive ? "sidebar-link--active" : ""}`}
                  title={collapsed ? item.label : undefined}
                >
                  <span className="sidebar-icon">{item.icon}</span>
                  {!collapsed && <span className="sidebar-label">{item.label}</span>}
                  {!collapsed && item.badge && (
                    <span className="sidebar-badge">{item.badge}</span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Project Footer Badge */}
      <div className="sidebar-footer">
        <div className="sidebar-project-badge">
          <span className="project-key-tag">{projectId || "KAN"}</span>
          {!collapsed && (
            <div className="project-name-sub">
              <strong>Jira Cloud</strong>
              <div style={{ fontSize: "0.7rem", color: "#10b981" }}>● Synchronized</div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
