"""
Mock Executor for Paper Trading
Claire de Binaire Trading Bot
"""

import uuid
import random
from datetime import datetime
from typing import Optional
from models import Order, ExecutionResult, OrderStatus


class MockExecutor:
    """Simulates order execution without real API calls"""
    
    def __init__(self):
        self.orders = {}
        self.success_rate = 0.95  # 95% success rate
    
    def execute_order(self, order: Order) -> ExecutionResult:
        """
        Simulate order execution
        Returns ExecutionResult with simulated data
        """
        # Generate order ID
        order_id = f"MOCK_{uuid.uuid4().hex[:8]}"
        client_id = order.client_id or f"CDB_{uuid.uuid4().hex[:8]}"
        
        # Simulate success/failure
        success = random.random() < self.success_rate
        
        if success:
            # Simulate successful execution
            price = self._simulate_price(order.symbol)
            filled_quantity = order.quantity
            
            result = ExecutionResult(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=filled_quantity,
                status=OrderStatus.FILLED.value,
                price=price,
                client_id=client_id,
                error_message=None,
                timestamp=datetime.utcnow().isoformat()
            )
            
            # Store order
            self.orders[order_id] = result
            
            return result
        
        else:
            # Simulate rejection
            result = ExecutionResult(
                order_id=order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                filled_quantity=0.0,
                status=OrderStatus.REJECTED.value,
                price=None,
                client_id=client_id,
                error_message="Mock rejection: Insufficient liquidity",
                timestamp=datetime.utcnow().isoformat()
            )
            
            return result
    
    def _simulate_price(self, symbol: str) -> float:
        """
        Simulate realistic price based on symbol
        """
        # Simple price simulation
        if "BTC" in symbol:
            base_price = 50000
        elif "ETH" in symbol:
            base_price = 3000
        else:
            base_price = 100
        
        # Add random variance (-0.1% to +0.1%)
        variance = random.uniform(-0.001, 0.001)
        price = base_price * (1 + variance)
        
        return round(price, 2)
    
    def get_order_status(self, order_id: str) -> Optional[ExecutionResult]:
        """Get status of a mock order"""
        return self.orders.get(order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel a mock order (always succeeds)"""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED.value
            return True
        return False
