from __future__ import annotations

import logging
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


# 1. ENUM TRẠNG THÁI
class SeatState(Enum):
    AVAILABLE = "AVAILABLE"
    HOLD = "HOLD"
    SOLD = "SOLD"


# 2. ENUM EVENT
class SeatEvent(Enum):
    HOLD_SEAT = "HOLD_SEAT"
    CANCEL_HOLD = "CANCEL_HOLD"
    EXPIRE_HOLD = "EXPIRE_HOLD"
    PAYMENT_SUCCESS = "PAYMENT_SUCCESS"
    PAYMENT_FAILED = "PAYMENT_FAILED"


class PaymentStatus(Enum):
    NONE = "NONE"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# 3. EXCEPTION
class InvalidTransitionError(Exception):
    pass


# 4. TRANSITION TABLE
VALID_TRANSITIONS = {
    SeatState.AVAILABLE: 
    {
        SeatEvent.HOLD_SEAT: SeatState.HOLD,
    },
    SeatState.HOLD: 
    {
        SeatEvent.CANCEL_HOLD: SeatState.AVAILABLE,
        SeatEvent.EXPIRE_HOLD: SeatState.AVAILABLE,
        SeatEvent.PAYMENT_SUCCESS: SeatState.SOLD,
        SeatEvent.PAYMENT_FAILED: SeatState.AVAILABLE,
    },
    SeatState.SOLD: {},
}

# LOGGING
logger = logging.getLogger(__name__)


#SEAT FSM
@dataclass
class SeatFSM:
    seat_id: str
    state: SeatState = SeatState.AVAILABLE
    holder_id: str | None = None
    hold_until: datetime | None = None
    payment_status: PaymentStatus = PaymentStatus.NONE
    _history: list[dict[str, str]] = field(default_factory=list, init=False)

    #STATE TRANSITION VALIDATION 
    def transition(self, event: SeatEvent) -> SeatState:

        current_state = self.state
        next_state = VALID_TRANSITIONS.get(current_state, {}).get(event)

        #STATE TRANSITION VALIDATION 
        if next_state is None:
            message = (f"Invalid transition: {current_state.value} + {event.value}")
            logger.error("Seat %s: %s", self.seat_id, message,)
            raise InvalidTransitionError(f"khong the chuyen ghe {self.seat_id} " f"tu {current_state.value} voi event {event.value}")

        self.state = next_state

        # Cập nhật dữ liệu phụ thuộc vào event.
        self._update_data_after_transition(event)

        # Lưu history sau khi transition hợp lệ.
        self._history.append(
            {
                "seat_id": self.seat_id,
                "from": current_state.value,
                "event": event.value,
                "to": next_state.value,
            }
        )

        logger.info("Seat %s: %s --%s--> %s", self.seat_id, current_state.value, event.value, next_state.value,)

        return self.state

    def _update_data_after_transition(self, event: SeatEvent) -> None:

        if event == SeatEvent.HOLD_SEAT:
            self.payment_status = PaymentStatus.NONE

        elif event == SeatEvent.PAYMENT_SUCCESS:
            self.payment_status = PaymentStatus.SUCCESS
            self._clear_hold_data()

        elif event == SeatEvent.PAYMENT_FAILED:
            self.payment_status = PaymentStatus.FAILED
            self._clear_hold_data()

        elif event in (SeatEvent.CANCEL_HOLD, SeatEvent.EXPIRE_HOLD):
            self._clear_hold_data()

    def _clear_hold_data(self) -> None:
        self.holder_id = None
        self.hold_until = None

    # API
    def hold(self, user_id: str, hold_until: datetime) -> SeatState:
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id khong duoc bo trong.")

        if not isinstance(hold_until, datetime):
            raise TypeError("hold_until phai la datetime.")

        if hold_until <= datetime.now(hold_until.tzinfo):
            raise ValueError("hold_until phai la thoi diem trong tuong lai.")

        return self.transition(SeatEvent.HOLD_SEAT)

    def pay(self, success: bool) -> SeatState:

        event = (
            SeatEvent.PAYMENT_SUCCESS
            if success
            else SeatEvent.PAYMENT_FAILED
        )

        return self.transition(event)

    def cancel_hold(self) -> SeatState:
        return self.transition(SeatEvent.CANCEL_HOLD)

    def expire_hold(self) -> SeatState:
        return self.transition(SeatEvent.EXPIRE_HOLD)

    def is_hold_expired(self, now: datetime | None = None) -> bool:

        if self.state != SeatState.HOLD:
            return False

        if self.hold_until is None:
            return False

        if now is None:
            now = datetime.now(self.hold_until.tzinfo)

        return now >= self.hold_until

    def get_history(self) -> list[dict[str, str]]:
        return [record.copy() for record in self._history]


#DEMO
def demo() -> None:
    print("=" * 65)
    print("DEMO - MODULE QUAN LY TRANG THAI GHE")
    print("=" * 65)

    print("\n[A01] Thanh toan thanh cong")

    seat_a01 = SeatFSM("A01")
    print(f"Ban đầu: {seat_a01.seat_id} = {seat_a01.state.value}")

    seat_a01.hold("U001", datetime.now() + timedelta(minutes=10),)
