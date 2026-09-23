import subprocess
import logging
import platform

logger = logging.getLogger("kolon_monitor.toast")

def show_toast(title: str, message: str, risk_level: str = "INFO"):
    """
    Shows a native Windows Toast Notification using PowerShell.
    Works on Windows 10 & 11 without requiring extra DLLs or packages.
    """
    if platform.system() != "Windows":
        return

    # Clean text to prevent PowerShell script syntax issues
    safe_title = title.replace('"', '`"').replace("'", " ").replace("\n", " ")[:60]
    safe_msg = message.replace('"', '`"').replace("'", " ").replace("\n", " ")[:120]
    
    prefix = ""
    if risk_level == "HIGH":
        prefix = "🚨 [긴급/고위험] "
    elif risk_level == "MEDIUM":
        prefix = "⚠️ [주의/하자] "

    display_title = f"{prefix}{safe_title}"

    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
    $template = @"
    <toast>
        <visual>
            <binding template="ToastGeneric">
                <text>{display_title}</text>
                <text>{safe_msg}</text>
            </binding>
        </visual>
    </toast>
"@
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("코오롱글로벌·하늘채 모니터링").Show($toast)
    """

    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        )
    except Exception as e:
        logger.warning(f"Failed to show Windows toast: {e}")
