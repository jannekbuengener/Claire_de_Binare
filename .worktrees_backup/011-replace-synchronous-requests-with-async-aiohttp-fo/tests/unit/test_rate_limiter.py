"""
Unit Tests für Rate Limiter (Issue #202)

Testet:
- Token Bucket Algorithmus
- Thread-Safety
- Timeout-Verhalten
- MEXC-spezifische Limiter
"""

import pytest
import time
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from core.utils.rate_limiter import (
    RateLimiter,
    MexcRateLimiters,
    RateLimitException,
)


class TestRateLimiterBasic:
    """Grundlegende Rate Limiter Tests."""

    @pytest.mark.unit
    def test_acquire_within_limit(self):
        """Requests innerhalb des Limits werden akzeptiert."""
        limiter = RateLimiter(max_requests=5, time_window=1.0)

        # 5 Requests sollten erfolgreich sein
        for i in range(5):
            assert limiter.acquire(), f"Request {i+1} should succeed"

    @pytest.mark.unit
    def test_acquire_exceeds_limit(self):
        """Request über dem Limit wird abgelehnt."""
        limiter = RateLimiter(max_requests=3, time_window=1.0)

        # 3 Requests erfolgreich
        for _ in range(3):
            assert limiter.acquire()

        # 4. Request wird abgelehnt
        assert not limiter.acquire()

    @pytest.mark.unit
    def test_tokens_expire_after_window(self):
        """Tokens laufen nach time_window ab."""
        limiter = RateLimiter(max_requests=2, time_window=0.1)

        # Limit ausschöpfen
        assert limiter.acquire()
        assert limiter.acquire()
        assert not limiter.acquire()

        # Warten bis Tokens ablaufen
        time.sleep(0.15)

        # Jetzt wieder verfügbar
        assert limiter.acquire()

    @pytest.mark.unit
    def test_available_tokens(self):
        """available_tokens Property funktioniert korrekt."""
        limiter = RateLimiter(max_requests=5, time_window=1.0)

        assert limiter.available_tokens == 5

        limiter.acquire()
        assert limiter.available_tokens == 4

        limiter.acquire()
        limiter.acquire()
        assert limiter.available_tokens == 2

    @pytest.mark.unit
    def test_utilization(self):
        """utilization Property gibt korrekte Werte zurück."""
        limiter = RateLimiter(max_requests=4, time_window=1.0)

        assert limiter.utilization == 0.0

        limiter.acquire()
        assert limiter.utilization == 0.25

        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert limiter.utilization == 1.0

    @pytest.mark.unit
    def test_reset(self):
        """reset() löscht alle Tokens."""
        limiter = RateLimiter(max_requests=3, time_window=1.0)

        limiter.acquire()
        limiter.acquire()
        limiter.acquire()
        assert limiter.available_tokens == 0

        limiter.reset()
        assert limiter.available_tokens == 3

    @pytest.mark.unit
    def test_invalid_max_requests(self):
        """Ungültige max_requests wirft ValueError."""
        with pytest.raises(ValueError):
            RateLimiter(max_requests=0, time_window=1.0)

        with pytest.raises(ValueError):
            RateLimiter(max_requests=-1, time_window=1.0)

    @pytest.mark.unit
    def test_invalid_time_window(self):
        """Ungültige time_window wirft ValueError."""
        with pytest.raises(ValueError):
            RateLimiter(max_requests=5, time_window=0)

        with pytest.raises(ValueError):
            RateLimiter(max_requests=5, time_window=-1)


class TestRateLimiterWaitAndAcquire:
    """Tests für wait_and_acquire Methode."""

    @pytest.mark.unit
    def test_wait_and_acquire_immediate(self):
        """wait_and_acquire kehrt sofort zurück wenn Tokens verfügbar."""
        limiter = RateLimiter(max_requests=5, time_window=1.0)

        start = time.time()
        result = limiter.wait_and_acquire(timeout=1.0)
        duration = time.time() - start

        assert result is True
        assert duration < 0.1  # Sollte sofort sein

    @pytest.mark.unit
    def test_wait_and_acquire_waits_for_token(self):
        """wait_and_acquire wartet auf freies Token."""
        limiter = RateLimiter(max_requests=1, time_window=0.2)

        # Token verbrauchen
        limiter.acquire()

        # Warten auf neues Token
        start = time.time()
        result = limiter.wait_and_acquire(timeout=1.0)
        duration = time.time() - start

        assert result is True
        assert 0.15 < duration < 0.5  # Sollte ~0.2s warten

    @pytest.mark.unit
    def test_wait_and_acquire_timeout(self):
        """wait_and_acquire gibt False bei Timeout zurück."""
        limiter = RateLimiter(max_requests=1, time_window=10.0)

        # Token verbrauchen
        limiter.acquire()

        # Timeout nach 0.1s
        start = time.time()
        result = limiter.wait_and_acquire(timeout=0.1)
        duration = time.time() - start

        assert result is False
        assert duration < 0.2  # Sollte nach Timeout aufhören


class TestRateLimiterThreadSafety:
    """Tests für Thread-Safety."""

    @pytest.mark.unit
    def test_concurrent_acquire(self):
        """Concurrent acquires überschreiten nie das Limit."""
        limiter = RateLimiter(max_requests=10, time_window=1.0)
        successes = []
        failures = []

        def try_acquire():
            result = limiter.acquire()
            if result:
                successes.append(1)
            else:
                failures.append(1)

        # 20 Threads versuchen gleichzeitig zu acquiren
        threads = [Thread(target=try_acquire) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Genau 10 sollten erfolgreich sein
        assert len(successes) == 10
        assert len(failures) == 10

    @pytest.mark.unit
    def test_concurrent_wait_and_acquire(self):
        """Concurrent wait_and_acquire funktioniert korrekt."""
        limiter = RateLimiter(max_requests=5, time_window=0.1)
        results = []

        def try_acquire():
            result = limiter.wait_and_acquire(timeout=1.0)
            results.append(result)

        # 10 Threads, alle sollten nach und nach durchkommen
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(try_acquire) for _ in range(10)]
            for f in futures:
                f.result()

        # Alle sollten erfolgreich sein (Tokens refreshen sich)
        assert all(results)
        assert len(results) == 10


class TestMexcRateLimiters:
    """Tests für MEXC-spezifische Limiter."""

    @pytest.mark.unit
    def test_mexc_limiters_initialized(self):
        """MEXC Limiters sind korrekt initialisiert."""
        limiters = MexcRateLimiters()

        assert limiters.general.max_requests == 15
        assert limiters.general.time_window == 1.0

        assert limiters.orders.max_requests == 80
        assert limiters.orders.time_window == 10.0

        assert limiters.account.max_requests == 8
        assert limiters.account.time_window == 1.0

    @pytest.mark.unit
    def test_acquire_general(self):
        """acquire_general funktioniert."""
        limiters = MexcRateLimiters()

        assert limiters.acquire_general(timeout=0.1)
        assert limiters.general.available_tokens == 14

    @pytest.mark.unit
    def test_acquire_order_uses_both_limiters(self):
        """acquire_order verbraucht general UND orders Token."""
        limiters = MexcRateLimiters()

        assert limiters.acquire_order(timeout=0.1)

        # Beide Limiter sollten ein Token weniger haben
        assert limiters.general.available_tokens == 14
        assert limiters.orders.available_tokens == 79

    @pytest.mark.unit
    def test_acquire_account_uses_both_limiters(self):
        """acquire_account verbraucht general UND account Token."""
        limiters = MexcRateLimiters()

        assert limiters.acquire_account(timeout=0.1)

        assert limiters.general.available_tokens == 14
        assert limiters.account.available_tokens == 7
