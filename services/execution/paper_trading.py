"""
Paper Trading Engine

Simulates trading operations without real money for validation and testing purposes.
Provides comprehensive logging and performance tracking for 72-hour testing protocol.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import time
import threading


class OrderType(Enum):
    """Order types for paper trading"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status types"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class PaperOrder:
    """Paper trading order"""
    id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: datetime = None
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class PaperPosition:
    """Paper trading position"""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    created_at: datetime
    updated_at: datetime


class PaperTradingEngine:
    """
    Paper trading engine for 72-hour validation testing
    
    Simulates real trading operations with comprehensive logging
    and performance tracking capabilities.
    """
    
    def __init__(self, initial_balance: float = 100000.0, log_level: int = logging.INFO):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.positions: Dict[str, PaperPosition] = {}
        self.orders: Dict[str, PaperOrder] = {}
        self.trade_history: List[Dict[str, Any]] = []
        self.performance_metrics: Dict[str, Any] = {}
        
        # Setup logging
        self.logger = self._setup_logging(log_level)
        
        # Trading state
        self.is_active = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
        # Market data simulation
        self.market_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = initial_balance
        
        self.logger.info(f"Paper trading engine initialized with balance: ${initial_balance:,.2f}")
    
    def _setup_logging(self, log_level: int) -> logging.Logger:
        """Setup logging for paper trading engine"""
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # File handler for paper trading logs
        file_handler = logging.FileHandler(f"logs/paper_trading_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log")
        file_handler.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def start_paper_trading(self):
        """Start paper trading session"""
        self.is_active = True
        self.start_time = datetime.utcnow()
        self.logger.info("Paper trading session started")
    
    def stop_paper_trading(self):
        """Stop paper trading session"""
        self.is_active = False
        self.end_time = datetime.utcnow()
        self.logger.info("Paper trading session stopped")
        
        # Calculate final performance metrics
        self._calculate_final_metrics()
    
    def update_market_price(self, symbol: str, price: float):
        """Update market price for symbol"""
        timestamp = datetime.utcnow()
        
        # Store current price
        self.market_prices[symbol] = price
        
        # Store price history
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append((timestamp, price))
        
        # Update position PnL
        if symbol in self.positions:
            self._update_position_pnl(symbol, price)
        
        # Check for order fills
        self._check_order_fills(symbol, price)
    
    def place_order(self, symbol: str, side: str, quantity: float, 
                   order_type: OrderType = OrderType.MARKET, 
                   price: Optional[float] = None, 
                   stop_price: Optional[float] = None) -> str:
        """
        Place a paper trading order
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            quantity: Order quantity
            order_type: Type of order
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            
        Returns:
            Order ID
        """
        if not self.is_active:
            raise RuntimeError("Paper trading session not active")
        
        order_id = f"paper_{int(time.time() * 1000)}"
        
        order = PaperOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            stop_price=stop_price
        )
        
        # Validate order
        validation_result = self._validate_order(order)
        if not validation_result["valid"]:
            order.status = OrderStatus.REJECTED
            self.logger.warning(f"Order rejected: {validation_result['reason']}")
            return order_id
        
        self.orders[order_id] = order
        
        # Try immediate fill for market orders
        if order_type == OrderType.MARKET and symbol in self.market_prices:
            self._execute_order(order, self.market_prices[symbol])
        
        self.logger.info(f"Order placed: {order.side} {order.quantity} {order.symbol} @ {order.order_type.value}")
        
        return order_id
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CANCELLED
            self.logger.info(f"Order cancelled: {order_id}")
            return True
        
        return False
    
    def get_position(self, symbol: str) -> Optional[PaperPosition]:
        """Get current position for symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, PaperPosition]:
        """Get all current positions"""
        return self.positions.copy()
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get order status"""
        order = self.orders.get(order_id)
        return order.status if order else None
    
    def get_balance(self) -> float:
        """Get current balance"""
        return self.current_balance
    
    def get_equity(self) -> float:
        """Get current equity (balance + unrealized PnL)"""
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.current_balance + unrealized_pnl
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.winning_trades / max(self.total_trades, 1),
            "total_pnl": self.total_pnl,
            "balance": self.current_balance,
            "equity": self.get_equity(),
            "max_drawdown": self.max_drawdown,
            "return_percentage": ((self.get_equity() - self.initial_balance) / self.initial_balance) * 100,
            "active_positions": len(self.positions),
            "pending_orders": len([o for o in self.orders.values() if o.status == OrderStatus.PENDING])
        }
    
    def _validate_order(self, order: PaperOrder) -> Dict[str, Any]:
        """Validate order parameters"""
        # Check balance for buy orders
        if order.side == "buy":
            required_capital = order.quantity * (order.price or self.market_prices.get(order.symbol, 0))
            if required_capital > self.current_balance:
                return {"valid": False, "reason": "Insufficient balance"}
        
        # Check position for sell orders
        elif order.side == "sell":
            position = self.positions.get(order.symbol)
            if not position or position.quantity < order.quantity:
                return {"valid": False, "reason": "Insufficient position"}
        
        return {"valid": True, "reason": None}
    
    def _check_order_fills(self, symbol: str, price: float):
        """Check if any orders should be filled at current price"""
        symbol_orders = [o for o in self.orders.values() 
                        if o.symbol == symbol and o.status == OrderStatus.PENDING]
        
        for order in symbol_orders:
            should_fill = False
            fill_price = price
            
            if order.order_type == OrderType.MARKET:
                should_fill = True
            elif order.order_type == OrderType.LIMIT:
                if order.side == "buy" and price <= order.price:
                    should_fill = True
                    fill_price = order.price
                elif order.side == "sell" and price >= order.price:
                    should_fill = True
                    fill_price = order.price
            elif order.order_type == OrderType.STOP:
                if order.side == "buy" and price >= order.stop_price:
                    should_fill = True
                elif order.side == "sell" and price <= order.stop_price:
                    should_fill = True
            
            if should_fill:
                self._execute_order(order, fill_price)
    
    def _execute_order(self, order: PaperOrder, fill_price: float):
        """Execute an order"""
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()
        order.filled_price = fill_price
        
        # Update balance and positions
        if order.side == "buy":
            self._open_or_add_position(order.symbol, order.quantity, fill_price)
            self.current_balance -= order.quantity * fill_price
        else:  # sell
            realized_pnl = self._close_or_reduce_position(order.symbol, order.quantity, fill_price)
            self.current_balance += order.quantity * fill_price
            self.total_pnl += realized_pnl
        
        # Track trade
        self.total_trades += 1
        if order.side == "sell":
            # Determine if winning or losing trade
            position = self.positions.get(order.symbol)
            if position and realized_pnl > 0:
                self.winning_trades += 1
            elif realized_pnl < 0:
                self.losing_trades += 1
        
        # Update drawdown
        current_equity = self.get_equity()
        if current_equity > self.peak_balance:
            self.peak_balance = current_equity
        else:
            drawdown = (self.peak_balance - current_equity) / self.peak_balance
            self.max_drawdown = max(self.max_drawdown, drawdown)
        
        # Log trade
        trade_info = {
            "timestamp": order.filled_at.isoformat(),
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "price": fill_price,
            "value": order.quantity * fill_price,
            "balance": self.current_balance,
            "equity": current_equity
        }
        self.trade_history.append(trade_info)
        
        self.logger.info(f"Order executed: {order.side} {order.quantity} {order.symbol} @ ${fill_price:.2f}")
    
    def _open_or_add_position(self, symbol: str, quantity: float, price: float):
        """Open new position or add to existing position"""
        if symbol in self.positions:
            # Add to existing position
            position = self.positions[symbol]
            total_value = (position.quantity * position.average_price) + (quantity * price)
            total_quantity = position.quantity + quantity
            position.average_price = total_value / total_quantity
            position.quantity = total_quantity
            position.updated_at = datetime.utcnow()
        else:
            # Create new position
            self.positions[symbol] = PaperPosition(
                symbol=symbol,
                quantity=quantity,
                average_price=price,
                current_price=price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
    
    def _close_or_reduce_position(self, symbol: str, quantity: float, price: float) -> float:
        """Close or reduce position and return realized PnL"""
        if symbol not in self.positions:
            return 0.0
        
        position = self.positions[symbol]
        realized_pnl = (price - position.average_price) * quantity
        
        position.quantity -= quantity
        position.realized_pnl += realized_pnl
        position.updated_at = datetime.utcnow()
        
        # Remove position if quantity is zero
        if position.quantity <= 0:
            del self.positions[symbol]
        
        return realized_pnl
    
    def _update_position_pnl(self, symbol: str, current_price: float):
        """Update position unrealized PnL"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = current_price
            position.unrealized_pnl = (current_price - position.average_price) * position.quantity
            position.updated_at = datetime.utcnow()
    
    def _calculate_final_metrics(self):
        """Calculate final performance metrics"""
        if not self.start_time or not self.end_time:
            return
        
        duration = self.end_time - self.start_time
        final_equity = self.get_equity()
        
        self.performance_metrics = {
            "session_duration_hours": duration.total_seconds() / 3600,
            "initial_balance": self.initial_balance,
            "final_balance": self.current_balance,
            "final_equity": final_equity,
            "total_return": final_equity - self.initial_balance,
            "return_percentage": ((final_equity - self.initial_balance) / self.initial_balance) * 100,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.winning_trades / max(self.total_trades, 1),
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self._calculate_sharpe_ratio(),
            "average_trade_pnl": self.total_pnl / max(self.total_trades, 1),
            "positions_at_end": len(self.positions),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat()
        }
        
        self.logger.info(f"Final performance: {self.performance_metrics}")
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio (simplified)"""
        if not self.trade_history or len(self.trade_history) < 2:
            return 0.0
        
        # Calculate daily returns (simplified)
        returns = []
        for i in range(1, len(self.trade_history)):
            prev_equity = self.trade_history[i-1]["equity"]
            curr_equity = self.trade_history[i]["equity"]
            daily_return = (curr_equity - prev_equity) / prev_equity
            returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        return (mean_return * 365) / (std_dev * (365 ** 0.5)) if std_dev > 0 else 0.0
    
    def export_results(self) -> Dict[str, Any]:
        """Export all trading results for analysis"""
        return {
            "performance_metrics": self.performance_metrics,
            "trade_history": self.trade_history,
            "final_positions": {k: asdict(v) for k, v in self.positions.items()},
            "order_history": {k: asdict(v) for k, v in self.orders.items()},
            "price_history": self.price_history
        }