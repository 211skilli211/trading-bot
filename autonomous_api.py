#!/usr/bin/env python3
"""
Autonomous Controller API Endpoints
===================================
Flask API endpoints for the autonomous trading agent.

Add these routes to dashboard.py:
    from autonomous_api import register_autonomous_routes
    register_autonomous_routes(app)
"""

from flask import jsonify, request
from datetime import datetime, timezone
import logging

# Import autonomous components
try:
    from autonomous_controller import get_autonomous_controller, AutonomousDecision
    from dynamic_config_manager import get_dynamic_config_manager
    from intelligent_alerts import get_intelligent_alert_system
    from self_healing_engine import get_self_healing_engine
    AUTONOMOUS_AVAILABLE = True
except ImportError as e:
    AUTONOMOUS_AVAILABLE = False
    logging.warning(f"Autonomous components not available: {e}")

logger = logging.getLogger(__name__)


def register_autonomous_routes(app):
    """Register all autonomous controller API routes with Flask app."""
    
    # =========================================================================
    # Autonomous Controller Endpoints
    # =========================================================================
    
    @app.route("/api/autonomous/status")
    def autonomous_status():
        """Get autonomous agent status and recent decisions."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Autonomous controller not available"
            })
        
        try:
            controller = get_autonomous_controller()
            return jsonify({
                "success": True,
                "data": controller.get_status()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/autonomous/toggle", methods=["POST"])
    def toggle_autonomous():
        """Enable or disable autonomous mode."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Autonomous controller not available"
            })
        
        try:
            data = request.get_json() or {}
            enabled = data.get('enabled', True)
            
            controller = get_autonomous_controller()
            controller.toggle_enabled(enabled)
            
            return jsonify({
                "success": True,
                "enabled": enabled,
                "message": f"Autonomous mode {'enabled' if enabled else 'disabled'}"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/autonomous/decisions")
    def get_decision_log():
        """Get log of autonomous decisions."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Autonomous controller not available"
            })
        
        try:
            limit = request.args.get('limit', 50, type=int)
            controller = get_autonomous_controller()
            
            return jsonify({
                "success": True,
                "decisions": controller.get_decision_history(limit)
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/autonomous/config", methods=["GET", "POST"])
    def autonomous_config():
        """Get or update autonomous behavior configuration."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Autonomous controller not available"
            })
        
        try:
            controller = get_autonomous_controller()
            
            if request.method == "GET":
                return jsonify({
                    "success": True,
                    "config": controller.config
                })
            
            else:  # POST
                data = request.get_json() or {}
                
                # Update allowed config values
                allowed_keys = [
                    'check_interval_seconds',
                    'min_confidence_threshold',
                    'max_daily_changes',
                    'paper_mode_only',
                    'regime_switching_enabled',
                    'dynamic_position_sizing',
                    'risk_auto_adjustment'
                ]
                
                for key in allowed_keys:
                    if key in data:
                        controller.config[key] = data[key]
                
                return jsonify({
                    "success": True,
                    "message": "Configuration updated",
                    "config": {k: controller.config.get(k) for k in allowed_keys}
                })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/autonomous/decisions/<decision_id>/approve", methods=["POST"])
    def approve_decision(decision_id):
        """Human approval of escalated decision."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Autonomous controller not available"
            })
        
        try:
            controller = get_autonomous_controller()
            success = controller.approve_decision(decision_id)
            
            return jsonify({
                "success": success,
                "message": "Decision approved" if success else "Decision not found"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/autonomous/decisions/<decision_id>/reject", methods=["POST"])
    def reject_decision(decision_id):
        """Human rejection of escalated decision."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Autonomous controller not available"
            })
        
        try:
            controller = get_autonomous_controller()
            success = controller.reject_decision(decision_id)
            
            return jsonify({
                "success": success,
                "message": "Decision rejected" if success else "Decision not found"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    # =========================================================================
    # Dynamic Configuration Endpoints
    # =========================================================================
    
    @app.route("/api/config/dynamic/status")
    def dynamic_config_status():
        """Get dynamic configuration status and adjustments."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Dynamic config manager not available"
            })
        
        try:
            manager = get_dynamic_config_manager()
            
            return jsonify({
                "success": True,
                "data": manager.get_adjustment_summary()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/config/dynamic/apply-regime", methods=["POST"])
    def apply_regime_config():
        """Manually apply regime-based configuration."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Dynamic config manager not available"
            })
        
        try:
            data = request.get_json() or {}
            regime = data.get('regime')
            
            if regime not in ['DEFENSIVE', 'NEUTRAL', 'RISK_ON']:
                return jsonify({
                    "success": False,
                    "error": "Invalid regime. Use DEFENSIVE, NEUTRAL, or RISK_ON"
                })
            
            import asyncio
            manager = get_dynamic_config_manager()
            changes = asyncio.run(manager.apply_regime_adjustments(regime))
            
            return jsonify({
                "success": True,
                "regime": regime,
                "changes_made": len(changes),
                "changes": [
                    {
                        "parameter": c.parameter_path,
                        "original": c.original_value,
                        "new": c.new_value
                    }
                    for c in changes
                ]
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/config/dynamic/rollback/<change_id>", methods=["POST"])
    def rollback_config_change(change_id):
        """Rollback a specific configuration change."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Dynamic config manager not available"
            })
        
        try:
            manager = get_dynamic_config_manager()
            success = manager.rollback_change(change_id)
            
            return jsonify({
                "success": success,
                "message": "Change rolled back" if success else "Change not found"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/config/dynamic/history")
    def config_change_history():
        """Get configuration change history."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Dynamic config manager not available"
            })
        
        try:
            limit = request.args.get('limit', 50, type=int)
            manager = get_dynamic_config_manager()
            
            return jsonify({
                "success": True,
                "history": manager.get_change_history(limit)
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    # =========================================================================
    # Intelligent Alerts Endpoints
    # =========================================================================
    
    @app.route("/api/alerts/intelligent/status")
    def intelligent_alerts_status():
        """Get intelligent alert system status."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Intelligent alert system not available"
            })
        
        try:
            alerts = get_intelligent_alert_system()
            
            return jsonify({
                "success": True,
                "stats": alerts.get_alert_stats()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/alerts/intelligent/active")
    def active_intelligent_alerts():
        """Get active intelligent alerts."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Intelligent alert system not available"
            })
        
        try:
            category = request.args.get('category')
            alerts = get_intelligent_alert_system()
            
            return jsonify({
                "success": True,
                "alerts": alerts.get_active_alerts(category)
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/alerts/intelligent/<alert_id>/acknowledge", methods=["POST"])
    def acknowledge_intelligent_alert(alert_id):
        """Acknowledge an intelligent alert."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Intelligent alert system not available"
            })
        
        try:
            alerts = get_intelligent_alert_system()
            success = alerts.acknowledge_alert(alert_id)
            
            return jsonify({
                "success": success,
                "message": "Alert acknowledged" if success else "Alert not found"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/alerts/intelligent/<alert_id>/resolve", methods=["POST"])
    def resolve_intelligent_alert(alert_id):
        """Mark an intelligent alert as resolved."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Intelligent alert system not available"
            })
        
        try:
            alerts = get_intelligent_alert_system()
            success = alerts.resolve_alert(alert_id)
            
            return jsonify({
                "success": success,
                "message": "Alert resolved" if success else "Alert not found"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    # =========================================================================
    # Self-Healing Endpoints
    # =========================================================================
    
    @app.route("/api/healing/status")
    def self_healing_status():
        """Get self-healing engine status."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Self-healing engine not available"
            })
        
        try:
            healer = get_self_healing_engine()
            
            return jsonify({
                "success": True,
                "data": healer.get_status()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/healing/issues")
    def active_healing_issues():
        """Get active issues being handled by self-healing."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Self-healing engine not available"
            })
        
        try:
            healer = get_self_healing_engine()
            
            return jsonify({
                "success": True,
                "issues": healer.get_active_issues()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/healing/issues/<issue_id>/remediate", methods=["POST"])
    def force_remediation(issue_id):
        """Manually trigger remediation for an issue."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Self-healing engine not available"
            })
        
        try:
            healer = get_self_healing_engine()
            success = healer.force_remediation(issue_id)
            
            return jsonify({
                "success": success,
                "message": "Remediation triggered" if success else "Issue not found"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/api/healing/toggle", methods=["POST"])
    def toggle_self_healing():
        """Enable or disable self-healing engine."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Self-healing engine not available"
            })
        
        try:
            data = request.get_json() or {}
            enabled = data.get('enabled', True)
            
            healer = get_self_healing_engine()
            healer.toggle(enabled)
            
            return jsonify({
                "success": True,
                "enabled": enabled,
                "running": healer.running
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    # =========================================================================
    # Consolidated Autonomous Dashboard Data
    # =========================================================================
    
    @app.route("/api/autonomous/dashboard")
    def autonomous_dashboard():
        """Get all autonomous system data for dashboard."""
        if not AUTONOMOUS_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Autonomous systems not available"
            })
        
        try:
            controller = get_autonomous_controller()
            config_manager = get_dynamic_config_manager()
            alerts = get_intelligent_alert_system()
            healer = get_self_healing_engine()
            
            return jsonify({
                "success": True,
                "data": {
                    "autonomous_controller": controller.get_status(),
                    "dynamic_config": config_manager.get_adjustment_summary(),
                    "intelligent_alerts": alerts.get_alert_stats(),
                    "self_healing": healer.get_status(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    logger.info("[AutonomousAPI] Routes registered")


# For testing
if __name__ == "__main__":
    from flask import Flask
    
    app = Flask(__name__)
    register_autonomous_routes(app)
    
    print("Autonomous API routes registered:")
    for rule in app.url_map.iter_rules():
        if 'api' in rule.rule and ('autonomous' in rule.rule or 'healing' in rule.rule or 'dynamic' in rule.rule):
            print(f"  {rule.methods} {rule.rule}")
