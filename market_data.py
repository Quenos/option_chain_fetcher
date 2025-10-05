import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread
from typing import Any, ClassVar, Dict, List

from tastytrade.streamer import DXLinkStreamer, Greeks, Quote, Trade

from session import ApplicationSession


class EventType(str, Enum):
    GREEKS = 'Greeks'
    TRADE = 'Trade'
    QUOTE = 'Quote'

@dataclass
class MarketData():
    database: Any = field(init=True, default=None)

    # singleton class
    _instance: ClassVar['MarketData'] = None

    _subscribed_symbols: Dict[str, List[str]] = field(init=False, default_factory=dict) 
    _new_symbols: Dict[str, List[str]] = field(init=False, default_factory=dict) 
    _cached_events: Dict[str, Dict[str, Any]] = field(init=False, default_factory=dict) 
    _stop_streaming: bool = field(init=False, default=False)
    _thread_runs: bool = field(init=False, default=False)

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MarketData, cls).__new__(cls)
        return cls._instance

    def __post_init__(self):
        if not hasattr(self, '_initialized'):
            self._new_symbols[EventType.GREEKS] = []
            self._new_symbols[EventType.TRADE] = []
            self._new_symbols[EventType.QUOTE] = []
            self._subscribed_symbols[EventType.GREEKS] = []
            self._subscribed_symbols[EventType.TRADE] = []
            self._subscribed_symbols[EventType.QUOTE] = []
            self._cached_events[EventType.GREEKS] = {}
            self._cached_events[EventType.TRADE] = {}
            self._cached_events[EventType.QUOTE] = {}
            self._initialized = True

    def subscribe_greeks(self, symbols: list[str]) -> List[Greeks] | None:
        return self._subscribe_symbol(EventType.GREEKS, symbols)

    def subscribe_trades(self, symbols: list[str]) -> List[Trade] | None:
        return self._subscribe_symbol(EventType.TRADE, symbols)
    
    def subscribe_quotes(self, symbols: list[str]) -> Quote:
        return self._subscribe_symbol(EventType.QUOTE, symbols)
    
    def get_greeks(self, symbols: list[str]) -> List[Greeks] | None:
        return self._get_events(EventType.GREEKS, symbols)

    def get_trades(self, symbols: list[str]) -> List[Trade] | None:
        return self._get_events(EventType.TRADE, symbols)
    
    def get_quotes(self, symbols: list[str]) -> Quote:
        return self._get_events(EventType.QUOTE, symbols)

    def start_streamer(self) -> None:
        if self._thread_runs:
            return
        self._thread_runs = True
        thread = Thread(target=self._streamer_thread, daemon=True)
        thread.start()

    def stop_streamer(self) -> None:
        self._stop_streaming = True
        time.sleep(5)
        self._thread_runs = False

    def _subscribe_symbol(self, event_type: EventType, symbols: List[str]) -> None:
        new_symbols = list(set(symbols) - set(self._subscribed_symbols[event_type]))
        if new_symbols:
            self._new_symbols[event_type] = new_symbols
            self._subscribed_symbols[event_type] = list(set(self._subscribed_symbols[event_type]) | set(symbols))
            time.sleep(5)

    def _get_events(self, event_type: EventType, symbols: List[str]) -> List[Greeks] | List[Trade] | List[Quote] | None:
        market_data = list(self._cached_events[event_type].values())
        market_data = [data for data in market_data if data.event_symbol in symbols]
        return market_data

    async def _fetch_data(self, event_type: EventType) -> None:
        event_type_map = {
            EventType.GREEKS: Greeks,
            EventType.TRADE: Trade,
            EventType.QUOTE: Quote
        }
        session = ApplicationSession().session
        async with DXLinkStreamer(session) as streamer:
            streamer.fill_event_time = True
            if self.database and not streamer.database:
                streamer.database = self.database
            while not self._stop_streaming:
                if self._new_symbols[event_type]:
                    await streamer.subscribe(event_type_map[event_type], symbols=self._new_symbols[event_type])
                    self._new_symbols[event_type] = []
                if self.database:
                    await asyncio.sleep(10)
                    continue
                event = streamer.get_event_nowait(event_type_map[event_type])
                if event:
                    self._cached_events[event_type][event.event_symbol] = event
                await asyncio.sleep(0.1)

    async def _start_streamers(self) -> None:
        await asyncio.gather(
            self._fetch_data(EventType.QUOTE),
            self._fetch_data(EventType.TRADE),
            self._fetch_data(EventType.GREEKS)
        )

    def _streamer_thread(self) -> None:
        asyncio.run(self._start_streamers())
