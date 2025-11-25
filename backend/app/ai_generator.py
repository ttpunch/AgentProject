import random
from datetime import datetime

def generate_maintenance_report(machines, anomalies):
    """
    Simulates an AI analysis of the system state.
    """
    
    total_machines = len(machines)
    total_anomalies = len(anomalies)
    
    # Determine Risk Level
    if total_anomalies == 0:
        risk_level = "LOW"
        risk_score = random.randint(90, 99)
    elif total_anomalies < 3:
        risk_level = "MODERATE"
        risk_score = random.randint(70, 89)
    else:
        risk_level = "CRITICAL"
        risk_score = random.randint(40, 69)

    # Generate Summary
    summary_templates = {
        "LOW": "System is operating within optimal parameters. Routine monitoring is recommended.",
        "MODERATE": "Minor irregularities detected. Scheduled maintenance is advised for affected units.",
        "CRITICAL": "Urgent attention required. Multiple anomalies detected indicating potential system failure."
    }
    summary = summary_templates[risk_level]

    # Generate Insights
    insights = []
    insights.append(f"System Health Score: {risk_score}/100")
    insights.append(f"Active Anomalies: {total_anomalies}")
    
    if total_anomalies > 0:
        most_critical_machine = anomalies[0]['machine_id']
        insights.append(f"Primary Concern: Machine {most_critical_machine}")
    else:
        insights.append("No immediate concerns identified.")

    # Generate Recommendations
    recommendations = []
    if risk_level == "LOW":
        recommendations.append("Continue standard operating procedures.")
        recommendations.append("Review sensor calibration next month.")
    elif risk_level == "MODERATE":
        recommendations.append("Inspect vibration sensors on flagged machines.")
        recommendations.append("Check lubrication levels.")
    else:
        recommendations.append("IMMEDIATE STOP: Inspect Machine " + (anomalies[0]['machine_id'] if anomalies else "Unknown"))
        recommendations.append("Full diagnostic scan required.")
        recommendations.append("Alert maintenance team.")

    return {
        "timestamp": datetime.now().isoformat(),
        "risk_level": risk_level,
        "risk_score": risk_score,
        "summary": summary,
        "insights": insights,
        "recommendations": recommendations
    }
