import logging
from typing import Dict, Any

class Logger:
    def __init__(self, name: str = "tcp_optimizer", level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log(self, message: str, level=logging.INFO):
        """Logs a message with a specified level."""
        if level == logging.DEBUG:
            self.logger.debug(message)
        elif level == logging.INFO:
            self.logger.info(message)
        elif level == logging.WARNING:
            self.logger.warning(message)
        elif level == logging.ERROR:
            self.logger.error(message)
        elif level == logging.CRITICAL:
            self.logger.critical(message)

    def log_comparison_report(self, before_speed: Dict[str, Any], after_speed: Dict[str, Any]):
        """Logs a comparison report for performance metrics."""
        self.log("Optimization Report: Before vs. After", level=logging.INFO)
        self.log(f"{'Metric':<12} {'Before':>15} {'After':>15} {'Change':>12}", level=logging.INFO)
        self.log("-" * 56, level=logging.INFO)

        metrics = ['Download', 'Upload', 'Ping']
        for metric in metrics:
            before_val = before_speed.get(metric.lower(), 0)
            after_val = after_speed.get(metric.lower(), 0)
            unit = "Mbit/s" if metric != 'Ping' else "ms"
            change_pct = 0
            if before_val > 0:
                change_pct = ((before_val - after_val) / before_val) * 100 if metric == 'Ping' else ((after_val - before_val) / before_val) * 100
            
            self.log(f"{metric:<12} {before_val:>12.2f} {unit} {after_val:>12.2f} {unit} {change_pct:>+8.1f}%", level=logging.INFO)