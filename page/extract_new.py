import requests
import pandas as pd
import math
import time
import pandas_ta as ta
import traceback
import argparse
import yfinance as yf
import warnings
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Union
from marshmallow import Schema, fields, EXCLUDE, pre_load, post_load
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
from sqlalchemy.types import VARCHAR, DOUBLE_PRECISION, DATE

# Special thanks to https://github.com/burakyilmaz321

warnings.filterwarnings("ignore", category=FutureWarning)

class InfoSchema(Schema):
    code = fields.String(data_key="fonKodu", allow_none=True)
    date = fields.Date(data_key="tarih", allow_none=True)
    price = fields.Float(data_key="fiyat", allow_none=True)
    title = fields.String(data_key="fonUnvan", allow_none=True)
    market_cap = fields.Float(data_key="portfoyBuyukluk", allow_none=True)
    number_of_shares = fields.Float(data_key="tedPaySayisi", allow_none=True)
    number_of_investors = fields.Float(data_key="kisiSayisi", allow_none=True)
    FundType = fields.String(data_key="fonUnvanTip", allow_none=True)  # Fund Type Derived
    UmbrellaFundType = fields.String(data_key="fonUnvanTur", allow_none=True)  # Umbrella Fund Type Derived
 
    @post_load
    def post_load_hook(self, output_data, **kwargs):
        output_data = {f: output_data.setdefault(f) for f in self.fields}
        return output_data

    class Meta:
        unknown = EXCLUDE


# Accepted periyod values by the TEFAS API (months)
_VALID_PERIODS = (1, 3, 6, 12, 36, 60)


def _months_back(start: Union[date, datetime]) -> int:
    """Convert a requested start date to the months-back `periyod` the
    TEFAS API accepts. Accepts either `date` or `datetime`.
    """
    if isinstance(start, datetime):
        start = start.date()
    delta_days = max(0, (date.today() - start).days)
    months_needed = math.ceil(delta_days / 30) + 1
    for period in _VALID_PERIODS:
        if period >= months_needed:
            return period
    return _VALID_PERIODS[-1]

class tefas_get:
    root_url = "https://www.tefas.gov.tr"
    price_endpoint = "/api/funds/fonFiyatBilgiGetir"
    list_endpoint = "/api/funds/fonGetiriBazliBilgiGetir"
    concurrently = False
    use_Proxy = False
    fon_type = "YAT"
    proxies = None

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Connection": "keep-alive",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Origin": "https://www.tefas.gov.tr",
            "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx",
        })

    def get_FundType_combobox_items(self, url, select_id):
        # Stub to prevent crash and network calls
        return ["Altın", "Hisse Senedi", "Değişken", "Borçlanma Araçları", "Serbest", "Katılım", "Kıymetli Madenler", "Karma", "Para Piyasası", "Fon Sepeti"]

    def get_UmbrellaFundType_combobox_items(self, url, select_id):
        # Stub to prevent crash and network calls
        return [
            ("DEGISEKEN_SEMSIYE_FONU", "Değişken Şemsiye Fonu"),
            ("HISSE_SEMSIYE_FONU", "Hisse Senedi Şemsiye Fonu"),
            ("FON_SEPETI_SEMSIYE_FONU", "Fon Sepeti Şemsiye Fonu"),
            ("KATILIM_SEMSIYE_FONU", "Katılım Şemsiye Fonu"),
            ("KIYMETLI_MADENLER_SEMSIYE_FONU", "Kıymetli Madenler Şemsiye Fonu"),
            ("PARA_PIYASASI_SEMSIYE_FONU", "Para Piyasası Şemsiye Fonu"),
            ("SERBEST_SEMSIYE_FONU", "Serbest Şemsiye Fonu"),
            ("BORCLANMA_SEMSIYE_FONU", "Borçlanma Araçları Şemsiye Fonu"),
            ("KARMA_SEMSIYE_FONU", "Karma Şemsiye Fonu")
        ]

    def _classify_fund_multiple(self, title: str, fonTurAciklama: str) -> List[str]:
        title_upper = title.upper() if title else ""
        tur_upper = fonTurAciklama.upper() if fonTurAciklama else ""
        categories = []
        
        # 1. Base classification on Umbrella type
        if "HİSSE" in tur_upper or "HISSE" in tur_upper:
            categories.append("Hisse Senedi")
        if "BORÇLANMA" in tur_upper or "BORCLANMA" in tur_upper:
            categories.append("Borçlanma Araçları")
        if "PARA PİYASASI" in tur_upper or "PARA PIYASASI" in tur_upper:
            categories.append("Para Piyasası")
        if "SERBEST" in tur_upper:
            categories.append("Serbest")
        if "FON SEPETİ" in tur_upper or "FON SEPETI" in tur_upper:
            categories.append("Fon Sepeti")
        if "KATILIM" in tur_upper:
            categories.append("Katılım")
        if "DEĞİŞKEN" in tur_upper or "DEGISKEN" in tur_upper:
            categories.append("Değişken")
        if "KIYMETLİ MADENLER" in tur_upper or "KIYMETLI MADENLER" in tur_upper:
            categories.append("Kıymetli Madenler")
        if "KARMA" in tur_upper:
            categories.append("Karma")
            
        # 2. Refine & add multiple based on Title/Umbrella keywords
        if "ALTIN" in title_upper or "ALTIN" in tur_upper:
            categories.append("Altın")
        if "GÜMÜŞ" in title_upper or "GUMUS" in title_upper:
            categories.append("Gümüş")
        if "EUROBOND" in title_upper:
            categories.append("Eurobond")
        if "KİRA SERTİFİKASI" in title_upper or "KIRA SERTIFIKASI" in title_upper or "KİRA SERTİFİKALARI" in title_upper or "KIRA SERTIFIKALARI" in title_upper:
            categories.append("Kira Sertifikaları")
        if "SÜRDÜRÜLEBİLİRLİK" in title_upper or "SURDURULEBILIRLIK" in title_upper:
            categories.append("Sürdürülebilirlik Fonları")
        if "HİSSE SENEDİ YOĞUN" in title_upper or "HISSE SENEDI YOGUN" in title_upper or "H.S.Y.F" in title_upper or "HSYF" in title_upper:
            categories.append("Hisse Senedi Yoğun")
        if "EMTİA" in title_upper or "EMTIA" in title_upper:
            categories.append("Emtia")
        if "ENDEKS" in title_upper:
            if "HİSSE" in title_upper or "HISSE" in title_upper:
                categories.append("Endeks Hisse Senedi")
            else:
                categories.append("Endeks")
        if "MUTLAK GETİRİ" in title_upper or "MUTLAK GETIRI" in title_upper:
            categories.append("Mutlak Getiri Hedefli")
        if "YABANCI" in title_upper:
            if "FON SEPETİ" in title_upper or "FON SEPETI" in title_upper:
                categories.append("Yabancı Fon Sepeti")
            else:
                categories.append("Yabancı")
        if "BORÇLANMA ARAÇLARI FON SEPETİ" in title_upper or "BORCLANMA ARACLARI FON SEPETI" in title_upper:
            categories.append("Borçlanma Araçları Fon Sepeti")
        if "ÇOKLU VARLIK" in title_upper or "COKLU VARLIK" in title_upper:
            categories.append("Çoklu Varlık")
        if "İŞTİRAK" in title_upper or "ISTIRAK" in title_upper:
            categories.append("İştirak")
        if "ALTERNATİF" in title_upper or "ALTERNATIF" in title_upper:
            categories.append("Alternatif")
        if "SEKTÖR" in title_upper or "SEKTOR" in title_upper:
            categories.append("Sektör")
        if "ÖZEL" in title_upper or "OZEL" in title_upper:
            categories.append("Özel")
        if "DENGELİ" in title_upper or "DENGELI" in title_upper:
            categories.append("Dengeli Değişken")
        if "AGRESİF" in title_upper or "AGRESIF" in title_upper:
            categories.append("Agresif Değişken")
        if "ÇALIŞAN" in title_upper or "CALISAN" in title_upper:
            categories.append("Çalışanlarına Yönelik")
        if "DÖVİZ" in title_upper or "DOVIZ" in title_upper:
            categories.append("Döviz")
        if "KISA VADELİ" in title_upper or "KISA VADELI" in title_upper:
            if "BORÇLANMA" in title_upper or "BORCLANMA" in title_upper:
                categories.append("Kısa Vadeli Borçlanma Araçları")
            else:
                categories.append("Kısa Vadeli")
        if "ORTA VADELİ" in title_upper or "ORTA VADELI" in title_upper:
            categories.append("Orta Vadeli")
        if "UZUN VADELİ" in title_upper or "UZUN VADELI" in title_upper:
            if "BORÇLANMA" in title_upper or "BORCLANMA" in title_upper:
                categories.append("Uzun Vadeli Borçlanma Araçları")
            else:
                categories.append("Uzun Vadeli")
                
        # Remove duplicates while preserving order
        unique_categories = list(dict.fromkeys(categories))
        if not unique_categories:
            unique_categories.append("Diğer")
            
        return unique_categories

    def fetch_info(self, FundType, UmbrellaFundType, start_date_initial, end_date_initial):
        # The old HTML/form-based pagination is retired. Use the new per-fund
        # JSON API and fan-out by fund code. Keep the same public signature
        # but ignore FundType/UmbrellaFundType filters (they're not provided
        # by the new endpoints) — we still return any available FundType
        # fields if present in the returned JSON.
        info_schema = InfoSchema(many=True)
        frames = []

        # determine the months-back period required by the new API
        period_months = _months_back(start_date_initial)

        # When callers previously requested data partitioned by FundType
        # or UmbrellaFundType they expected a wide result. The new API
        # returns per-fund series only, so we fetch fund codes and then
        # request each fund's series.
        codes = self._list_fund_codes(self.fon_type)

        print(f"Crawl Progress: Fetching price series for {min(1000, len(codes))} funds...")
        for i, code in enumerate(codes[:1000], 1):
            payload = {"fonKodu": code, "dil": "TR", "periyod": period_months}
            raw = self._do_post(payload)
            time.sleep(0.05)  # Avoid hammering the server and getting rate limited/blocked
            if not raw:
                continue
            try:
                rows = info_schema.load(raw)
            except Exception:
                continue
            frames.append(pd.DataFrame(rows, columns=info_schema.fields.keys()))
            if i % 100 == 0 or i == len(codes[:1000]):
                print(f"   [+] Processed {i}/{min(1000, len(codes))} funds...")

        if not frames:
            return pd.DataFrame()

        merged = pd.concat(frames, ignore_index=True)
        # filter by requested date window
        merged = merged[(merged["date"] >= start_date_initial.date()) & (merged["date"] <= end_date_initial.date())]
        return merged

    def fetch_info_serial(self, FundTypes, UmbrellaFundTypes, start_date_initial, end_date_initial):
        # Kept for backward compatibility but redirecting to high-speed method
        return self.fetch(
            start=start_date_initial.strftime("%Y-%m-%d"),
            end=end_date_initial.strftime("%Y-%m-%d"),
            FundType=(FundTypes != [""] and FundTypes != [] and FundTypes is not None),
            UmbrellaFundType=(UmbrellaFundTypes != [""] and UmbrellaFundTypes != [] and UmbrellaFundTypes is not None)
        )

    def fetch(
        self,
        start: Union[str, datetime],
        end: Optional[Union[str, datetime]] = None,
        columns: Optional[List[str]] = None,
        FundType: bool = False,
        UmbrellaFundType: bool = False,
    ):
        start_date_initial = datetime.strptime(start, "%Y-%m-%d")
        end_date_initial = datetime.strptime(end or start, "%Y-%m-%d")

        merged = pd.DataFrame()
        if FundType or UmbrellaFundType:
            print("Fetching fund list from TEFAS...")
            all_funds = self._list_funds_by_category(self.fon_type)
            print(f"Discovered {len(all_funds)} funds. Starting high-speed category ingestion...")
            all_rows = []
            for r in all_funds:
                code = r.get("fonKodu")
                title = r.get("fonUnvan", r.get("fonAd", ""))
                tur = r.get("fonTurAciklama", "")
                if not code:
                    continue
                
                row = {
                    "code": code,
                    "title": title,
                    "date": date.today(),
                    "price": 0.0,
                }
                if FundType:
                    classified_list = self._classify_fund_multiple(title, tur)
                    for classified in classified_list:
                        row_copy = row.copy()
                        row_copy["FundType"] = "FundType_" + classified
                        all_rows.append(row_copy)
                if UmbrellaFundType:
                    row["UmbrellaFundType"] = "UmbrellaFundType_" + tur
                    all_rows.append(row)
            merged = pd.DataFrame(all_rows)
        else:
            merged = self.fetch_info("", "", start_date_initial, end_date_initial)

        if columns and not merged.empty:
            available = [c for c in columns if c in merged.columns]
            merged = merged[available]
        return merged

    def _do_post(self, data: Dict[str, str]) -> Dict[str, str]:
        # Post JSON to the new tefas.gov.tr API endpoints and return the
        # `resultList` item (or empty list) to match the newer crawler logic.
        if not hasattr(self, 'session') or self.session is None:
            self.__init__()
        try:
            response = self.session.post(
                url=f"{self.root_url}{self.price_endpoint if 'fonKodu' in data else self.list_endpoint}",
                json=data,
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            result = body.get("resultList") or []
            if not result:
                print(f"DEBUG: Empty result returned. Status: {response.status_code}. Response: {response.text[:300]}")
            return result
        except Exception as e:
            print(f"_do_post error: {e}")
            return []

    def _parse_date(self, date: Union[str, datetime]) -> str:
        if isinstance(date, datetime):
            formatted = datetime.strftime(date, "%d.%m.%Y")
        elif isinstance(date, str):
            try:
                parsed = datetime.strptime(date, "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(
                    "Date string format is incorrect. " "It should be `YYYY-MM-DD`"
                ) from exc
            else:
                formatted = datetime.strftime(parsed, "%d.%m.%Y")
        else:
            raise ValueError(
                "`date` should be a string like 'YYYY-MM-DD' "
                "or a `datetime.datetime` object."
            )
        return formatted

    def _list_fund_codes(self, kind: str) -> List[str]:
        payload = {
            "dil": "TR",
            "fonTipi": kind,
            "kurucuKodu": None,
            "sfonTurKod": None,
            "fonTurAciklama": None,
            "islem": None,
            "fonTurKod": None,
            "fonGrubu": None,
            "donemGetiri1a": "1",
            "donemGetiri3a": "1",
            "donemGetiri6a": "1",
            "donemGetiri1y": "1",
            "donemGetiriyb": "1",
            "donemGetiri3y": "1",
            "donemGetiri5y": "1",
            "basTarih": None,
            "bitTarih": None,
            "calismaTipi": 2,
            "getiriOrani": "1",
        }
        rows = self._do_post(payload)
        return [r["fonKodu"] for r in rows if r.get("fonKodu")]

    def _list_funds_by_category(self, kind: str, fonTurKod: Optional[str] = None, sfonTurKod: Optional[str] = None) -> List[Dict]:
        payload = {
            "dil": "TR",
            "fonTipi": kind,
            "kurucuKodu": None,
            "sfonTurKod": sfonTurKod,
            "fonTurAciklama": None,
            "islem": None,
            "fonTurKod": fonTurKod,
            "fonGrubu": None,
            "donemGetiri1a": "1",
            "donemGetiri3a": "1",
            "donemGetiri6a": "1",
            "donemGetiri1y": "1",
            "donemGetiriyb": "1",
            "donemGetiri3y": "1",
            "donemGetiri5y": "1",
            "basTarih": None,
            "bitTarih": None,
            "calismaTipi": 2,
            "getiriOrani": "1",
        }
        return self._do_post(payload)

def calculate_ta(group):
    group_indexed = group.copy()
    group_indexed.set_index('date', inplace=True)
    
    # Include all necessary columns in group_complete
    group_complete = group[['date', 'close', 'market_cap', 'number_of_shares', 'number_of_investors', 'market_cap_per_investors']].copy()
    
    # Create complete date range and forward-fill missing values
    complete_date_range = pd.date_range(start=group_indexed.index.min(), end=group_indexed.index.max(), freq='D')
    group_complete = group_complete.set_index('date').reindex(complete_date_range).ffill().reset_index()
    group_complete.rename(columns={'index': 'date'}, inplace=True)
    
    # Initialize DataFrames with required columns
    group_complete_7d = pd.DataFrame(columns=['date', 'close_7d', 'market_cap_7d', 'number_of_shares_7d', 'number_of_investors_7d', 'market_cap_per_investors_7d'])
    group_complete_1m = pd.DataFrame(columns=['date', 'close_1m', 'market_cap_1m', 'number_of_shares_1m', 'number_of_investors_1m', 'market_cap_per_investors_1m'])
    group_complete_3m = pd.DataFrame(columns=['date', 'close_3m', 'market_cap_3m', 'number_of_shares_3m', 'number_of_investors_3m', 'market_cap_per_investors_3m'])
    group_complete_6m = pd.DataFrame(columns=['date', 'close_6m', 'market_cap_6m', 'number_of_shares_6m', 'number_of_investors_6m', 'market_cap_per_investors_6m'])
    group_complete_1y = pd.DataFrame(columns=['date', 'close_1y', 'market_cap_1y', 'number_of_shares_1y', 'number_of_investors_1y', 'market_cap_per_investors_1y'])
    group_complete_3y = pd.DataFrame(columns=['date', 'close_3y', 'market_cap_3y', 'number_of_shares_3y', 'number_of_investors_3y', 'market_cap_per_investors_3y'])
    
    # Assign values from group_complete to the corresponding columns in group_complete_7d
    group_complete_7d['date'] = group_complete['date'] + pd.DateOffset(days=7)
    group_complete_7d['close_7d'] = group_complete['close']
    group_complete_7d['market_cap_7d'] = group_complete['market_cap']
    group_complete_7d['number_of_shares_7d'] = group_complete['number_of_shares']
    group_complete_7d['number_of_investors_7d'] = group_complete['number_of_investors']
    group_complete_7d['market_cap_per_investors_7d'] = group_complete['market_cap_per_investors']
    
    # Similarly assign values for other time periods
    group_complete_1m['date'] = group_complete['date'] + pd.DateOffset(days=30)
    group_complete_1m['close_1m'] = group_complete['close']
    group_complete_1m['market_cap_1m'] = group_complete['market_cap']
    group_complete_1m['number_of_shares_1m'] = group_complete['number_of_shares']
    group_complete_1m['number_of_investors_1m'] = group_complete['number_of_investors']
    group_complete_1m['market_cap_per_investors_1m'] = group_complete['market_cap_per_investors']
    
    group_complete_3m['date'] = group_complete['date'] + pd.DateOffset(days=90)
    group_complete_3m['close_3m'] = group_complete['close']
    group_complete_3m['market_cap_3m'] = group_complete['market_cap']
    group_complete_3m['number_of_shares_3m'] = group_complete['number_of_shares']
    group_complete_3m['number_of_investors_3m'] = group_complete['number_of_investors']
    group_complete_3m['market_cap_per_investors_3m'] = group_complete['market_cap_per_investors']
    
    group_complete_6m['date'] = group_complete['date'] + pd.DateOffset(days=180)
    group_complete_6m['close_6m'] = group_complete['close']
    group_complete_6m['market_cap_6m'] = group_complete['market_cap']
    group_complete_6m['number_of_shares_6m'] = group_complete['number_of_shares']
    group_complete_6m['number_of_investors_6m'] = group_complete['number_of_investors']
    group_complete_6m['market_cap_per_investors_6m'] = group_complete['market_cap_per_investors']
    
    group_complete_1y['date'] = group_complete['date'] + pd.DateOffset(days=365)
    group_complete_1y['close_1y'] = group_complete['close']
    group_complete_1y['market_cap_1y'] = group_complete['market_cap']
    group_complete_1y['number_of_shares_1y'] = group_complete['number_of_shares']
    group_complete_1y['number_of_investors_1y'] = group_complete['number_of_investors']
    group_complete_1y['market_cap_per_investors_1y'] = group_complete['market_cap_per_investors']
    
    group_complete_3y['date'] = group_complete['date'] + pd.DateOffset(days=1095)
    group_complete_3y['close_3y'] = group_complete['close']
    group_complete_3y['market_cap_3y'] = group_complete['market_cap']
    group_complete_3y['number_of_shares_3y'] = group_complete['number_of_shares']
    group_complete_3y['number_of_investors_3y'] = group_complete['number_of_investors']
    group_complete_3y['market_cap_per_investors_3y'] = group_complete['market_cap_per_investors']
    
    # Perform left joins with group_indexed on the 'date' column
    group_indexed.reset_index(inplace=True)
    group_indexed = group_indexed.merge(group_complete_7d[['date', 'close_7d', 'market_cap_7d', 'number_of_shares_7d', 'number_of_investors_7d', 'market_cap_per_investors_7d']], on='date', how='left')
    group_indexed = group_indexed.merge(group_complete_1m[['date', 'close_1m', 'market_cap_1m', 'number_of_shares_1m', 'number_of_investors_1m', 'market_cap_per_investors_1m']], on='date', how='left')
    group_indexed = group_indexed.merge(group_complete_3m[['date', 'close_3m', 'market_cap_3m', 'number_of_shares_3m', 'number_of_investors_3m', 'market_cap_per_investors_3m']], on='date', how='left')
    group_indexed = group_indexed.merge(group_complete_6m[['date', 'close_6m', 'market_cap_6m', 'number_of_shares_6m', 'number_of_investors_6m', 'market_cap_per_investors_6m']], on='date', how='left')
    group_indexed = group_indexed.merge(group_complete_1y[['date', 'close_1y', 'market_cap_1y', 'number_of_shares_1y', 'number_of_investors_1y', 'market_cap_per_investors_1y']], on='date', how='left')
    group_indexed = group_indexed.merge(group_complete_3y[['date', 'close_3y', 'market_cap_3y', 'number_of_shares_3y', 'number_of_investors_3y', 'market_cap_per_investors_3y']], on='date', how='left')
    
    # Calculate technical indicators
    group_indexed.set_index('date', inplace=True)
    group_indexed["EMA_5"]   = ta.ema(group_indexed['close'], length=5)  # Exponential Moving Average (EMA)
    group_indexed["EMA_10"]  = ta.ema(group_indexed['close'], length=10) 
    group_indexed["EMA_12"]  = ta.ema(group_indexed['close'], length=12) 
    group_indexed["EMA_20"]  = ta.ema(group_indexed['close'], length=20) 
    group_indexed["EMA_26"]  = ta.ema(group_indexed['close'], length=26) 
    group_indexed["EMA_50"]  = ta.ema(group_indexed['close'], length=50) 
    group_indexed["EMA_100"] = ta.ema(group_indexed['close'], length=100)
    group_indexed["EMA_200"] = ta.ema(group_indexed['close'], length=200)
    group_indexed["SMA_5"]   = ta.sma(group_indexed['close'], length=5)  # Simple Moving Average (SMA)
    group_indexed["RSI_14"]  = ta.rsi(group_indexed['close'], length=14) # Relative Strength Index (RSI) with RMA
    group_indexed["MACD"]    = group_indexed["EMA_12"] - group_indexed["EMA_26"] # Moving Average Convergence Divergence (MACD)

    group_indexed.reset_index(inplace=True)
    return group_indexed

def main():

    parser = argparse.ArgumentParser(description="--tefas_price true --calculate_indicators true --tefas_fundtype true --timedelta 30")
    parser.add_argument('--tefas_price', type=str, required=False, help="Get tefas price data", default="true")
    parser.add_argument('--calculate_indicators', type=str, required=False, help="Calculate technical indicators", default="false")
    parser.add_argument('--tefas_fundtype', type=str, required=False, help="Get tefas fund type data", default="false")
    parser.add_argument('--timedelta', type=str, required=False, help="Number of days to look back for price data", default="30")

    args = parser.parse_args()
    tefas_price = args.tefas_price.lower() == 'true' or args.tefas_price.lower() == 'True'
    calculate_indicators = args.calculate_indicators.lower() == 'true' or args.calculate_indicators.lower() == 'True'
    tefas_fundtype = args.tefas_fundtype.lower() == 'true' or args.tefas_fundtype.lower() == 'True'
    timedelta_days = int(args.timedelta)
    timedelta_days = max(1, min(timedelta_days, 1500))  # Ensure between 1 and 365

    tefas = tefas_get()

    end_date = value=date.today()
    start_date = value=date.today() - timedelta(days=timedelta_days)
    print(f"Start Date: {start_date}, End Date: {end_date}")

    def db_engine():
        # is_docker = os.getenv("IS_DOCKER", "false").lower() == "true"
        # hostname = "tefas_postgres" if is_docker else "localhost"
        hostname = os.getenv("POSTGRES_HOST", "tefas_postgres")
        user = os.getenv("POSTGRES_USER", "tefas")
        password = os.getenv("POSTGRES_PASSWORD", "tefas")
        db = os.getenv("POSTGRES_DB", "tefas_db")
        port = os.getenv("POSTGRES_PORT", "5432")
        
        engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{hostname}:{port}/{db}')
        return engine

    def read_table(table_name, parse_dates=None):
        engine = db_engine()
        df = pd.read_sql(f'SELECT * FROM "{table_name}"', engine, parse_dates=parse_dates)
        engine.dispose()
        return df

    use_postgres = True

    def fetch_usd_try_rates(start_year=2020, end_year=None):
        try:
            if end_year is None:
                end_year = datetime.today().year

            if start_year > end_year:
                raise ValueError("start_year must be less than or equal to end_year")

            all_data = []

            for year in range(start_year, end_year + 1):
                start_date = f"{year}-01-01"
                if year == datetime.today().year:
                    end_date = datetime.today().date()
                else:
                    end_date = f"{year}-12-31"

                try:
                    if isinstance(end_date, str):
                        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

                    if start_date >= end_date:
                        print(f"Skipping year {year}: Invalid date range")
                        continue

                    usd_try = yf.Ticker("USDTRY=X")
                    data = usd_try.history(start=start_date, end=end_date + timedelta(days=1), interval="1d")
                    
                    if data.empty:
                        print(f"No data returned for USD/TRY for year {year}")
                        continue
                    
                    all_data.append(data)
                    print(f"Successfully fetched USD/TRY for {year}: {len(data)} days")

                except Exception as e:
                    print(f"Error fetching data for {year}: {e}")
                    continue

            if not all_data:
                print("No data fetched for any year")
                return None

            combined_data = pd.concat(all_data)
            return combined_data

        except Exception as e:
            print(f"Error in fetch_usd_try_rates: {e}")
            return None

    def fetch_gold_try_rates(start_year=2020, end_year=None):
        try:
            if end_year is None:
                end_year = datetime.today().year

            if start_year > end_year:
                raise ValueError("start_year must be less than or equal to end_year")

            all_data = []

            for year in range(start_year, end_year + 1):
                start_date = f"{year}-01-01"
                if year == datetime.today().year:
                    end_date = datetime.today().date()
                else:
                    end_date = f"{year}-12-31"

                try:
                    if isinstance(end_date, str):
                        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

                    if start_date >= end_date:
                        print(f"Skipping year {year}: Invalid date range")
                        continue

                    gold = yf.Ticker("GC=F")
                    data = gold.history(start=start_date, end=end_date + timedelta(days=1), interval="1d")
                    
                    if data.empty:
                        print(f"No data returned for Gold price for year {year}")
                        continue
                    
                    all_data.append(data)
                    print(f"Successfully fetched Gold price for {year}: {len(data)} days")

                except Exception as e:
                    print(f"Error fetching data for {year}: {e}")
                    continue

            if not all_data:
                print("No data fetched for any year")
                return None

            combined_data = pd.concat(all_data)
            return combined_data

        except Exception as e:
            print(f"Error in Gold price fetch: {e}")
            return None


    def insert_rates_to_db(data, table_name):
        engine = db_engine()
        try:
            data_reset = data.reset_index()
            data_reset['Date'] = data_reset['Date'].dt.strftime('%Y-%m-%d')
            data_reset = data_reset[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            data_reset.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            data_reset['volume'] = data_reset['volume'].fillna(0).astype(int)
            # data_reset.ffillna(method='ffill', inplace=True)
            data_reset.to_sql(
                    table_name,
                    engine,
                    if_exists="replace",
                    index=False,
                    dtype={
                        "date": DATE,
                        "open": DOUBLE_PRECISION,
                        "high": DOUBLE_PRECISION,
                        "low": DOUBLE_PRECISION,
                        "close": DOUBLE_PRECISION,
                        "volume": DOUBLE_PRECISION,
                    })
        except Exception as e:
            print(f"Error inserting {table_name}: {e}")
        finally:
            engine.dispose()
            print(f"{table_name} rates: {data_reset.shape[0]}  inserted into the database")

    try:
        data = fetch_usd_try_rates()
        if data is not None:
            insert_rates_to_db(data, "usd_try_rates")
        else:
            print("No USD/TRY data to insert into the database")
    except Exception as e:
        print(f"Error occurred FX Rates cannot be fetched: {str(e)}")

    try:
        data_gold = fetch_gold_try_rates()
        if data_gold is not None:
            insert_rates_to_db(data_gold, "gold_try_rates")
        else:
            print("No Gold data to insert into the database")
    except Exception as e:
        print(f"Error occurred Gold cannot be fetched: {str(e)}")

    if tefas_price: 
        date_start = start_date.strftime("%Y-%m-%d")
        date_end = end_date.strftime("%Y-%m-%d")

        fetched_data = tefas.fetch(start=date_start, end=date_end, columns=["code", "date", "price", "market_cap", "number_of_shares", "number_of_investors"], FundType=False, UmbrellaFundType=False)
        if fetched_data.empty:
            print("No price data was fetched from TEFAS (possibly due to network/SSL connection errors). Skipping database insertions.")
        else:
            fetched_data['date'] = pd.to_datetime(fetched_data['date'], errors='coerce')
            fetched_data['price'].astype(float,False)
            fetched_data.rename(columns={'price': 'close'}, inplace=True)
            fetched_data.rename(columns={'code': 'symbol'}, inplace=True)
            fetched_data['market_cap'].astype(float,False)
            fetched_data['number_of_shares'].astype(float,False)
            fetched_data['number_of_investors'].astype(float,False)
            fetched_data['date'] = fetched_data['date'].dt.strftime('%Y-%m-%d')
            fetched_data.dropna()
            fetched_data = fetched_data.drop_duplicates(subset=['symbol', 'date'])

            if use_postgres: 
                engine = db_engine()
                try:
                    with engine.connect() as conn:
                        trans = conn.begin()  
                        result = conn.execute( text("DELETE FROM tefas WHERE date >= :start AND date <= :end"), {'start': date_start, 'end': date_end} )
                        print(f"Rows deleted FROM tefas: {result.rowcount}")
                        trans.commit()
                except Exception as e:
                    print(f"An error occurred deleting tefas: {e}")
                    traceback.print_exc()
                engine.dispose()

            engine = db_engine()
            if use_postgres and engine is not None:
                try:
                    fetched_data.to_sql(
                        "tefas",
                        engine,
                        if_exists="append",  # "replace" or "append", or "fail"
                        index=False
                    )
                    print(f"TEFAS Price - {fetched_data.shape[0]} rows inserted into tefas table")
                except Exception as e:
                    print(f"An error occurred inserting tefas: {e}")
                    traceback.print_exc()

            engine.dispose()

    if calculate_indicators: 

        engine = db_engine()
        if use_postgres and engine is not None:
            try:
                fetched_data = pd.read_sql("SELECT * FROM tefas", engine, parse_dates=['date'])
            except Exception as e:
                print(f"An error occurred : {e}")
                traceback.print_exc()
                fetched_data = pd.DataFrame()
        engine.dispose()

        if fetched_data.empty:
            print("No price data in tefas table to calculate indicators. Skipping.")
        else:
            fetched_data['close'].astype(float,False)
            fetched_data['year'] = fetched_data['date'].dt.year
            fetched_data['week_no'] = fetched_data['date'].dt.isocalendar().week.astype(str).str.zfill(2)
            fetched_data['year_week'] = fetched_data['year'].astype(str) +'-'+ fetched_data['week_no'].astype(str)
            fetched_data['day_of_week'] = fetched_data['date'].dt.strftime('%A')
            fetched_data['market_cap_per_investors'] = fetched_data['market_cap'] / fetched_data['number_of_investors']
            fetched_data.sort_values(by=['symbol', 'date'], inplace=True)
            fetched_data['open'] = fetched_data.groupby('symbol')['close'].shift(1)
            fetched_data['high'] = fetched_data[['open', 'close']].max(axis=1)
            fetched_data['low'] = fetched_data[['open', 'close']].min(axis=1)
            fetched_data = fetched_data.groupby(['symbol']).apply(calculate_ta)
            fetched_data['date'] = fetched_data['date'].dt.strftime('%Y-%m-%d')

            engine = db_engine()
            with engine.connect() as conn:
                try:
                    trans = conn.begin()  
                    result = conn.execute( text("DELETE FROM tefas_transformed") )
                    print(f"Rows deleted FROM tefas_transformed: {result.rowcount}")
                    trans.commit()
                except Exception as e:
                    print(f"An error occurred: {e}")
                    traceback.print_exc()
            engine.dispose()

            engine = db_engine()
            if use_postgres and engine is not None:
                try:
                    fetched_data.to_sql(
                        "tefas_transformed",
                        engine,
                        if_exists="append",  # "replace" or "append", or "fail"
                        index=False
                    )
                except Exception as e:
                    print(f"An error occurred : {e}")
                    traceback.print_exc()
            engine.dispose()

    if tefas_fundtype:
        start_date_calc = date.today() - timedelta(days=timedelta_days)
        date_start = start_date_calc.strftime("%Y-%m-%d")
        date_end = date.today().strftime("%Y-%m-%d")

        print(f"Ingesting Fund Type structures from {date_start} to {date_end}...")
        fetched_data_fundtype = tefas.fetch(start=date_start, end=date_end, columns=["code", "date", "price", "FundType", "title"], FundType=True, UmbrellaFundType=False)
        if fetched_data_fundtype.empty:
            print("No fundtype data was fetched from TEFAS. Skipping tefas_funds table generation.")
        else:
            fetched_data_fundtype.drop_duplicates(subset=['code', 'FundType'], ignore_index=True, inplace=True)
            
            # Print one-line summary for each FundType
            print("\nIngested Fund Types details:")
            for ft, group in fetched_data_fundtype.groupby('FundType'):
                ft_clean = ft.replace('FundType_', '')
                codes_str = ", ".join(group['code'].unique())
                out_str = f"Fundtype <{ft_clean}>, Funds: {codes_str}"
                try:
                    print(out_str)
                except UnicodeEncodeError:
                    import unicodedata
                    normalized = unicodedata.normalize('NFKD', out_str).encode('ascii', 'ignore').decode('ascii')
                    print(normalized)
            print()

            fon_table_fundtype = fetched_data_fundtype.pivot_table(index=['title', 'code'], columns='FundType', aggfunc='size', fill_value=0)
            fon_table_fundtype.reset_index(inplace=True)
            fon_table_fundtype = fon_table_fundtype.map(lambda x: False if x == 0 else (True if x == 1 else x))
            fon_table_fundtype.rename(columns={'code': 'symbol'}, inplace=True)
            fon_table_fundtype['symbolwithtitle'] = fon_table_fundtype['symbol'].astype(str) +' - '+ fon_table_fundtype['title'].astype(str)
            print(f"   [+] Processed {fon_table_fundtype.shape[0]} unique fund types.")

            try:
                fetched_data_umbrellafundtype = tefas.fetch(start=date_start, end=date_end, columns=["code", "date", "price", "UmbrellaFundType", "title"], FundType=False, UmbrellaFundType=True)
                if fetched_data_umbrellafundtype.empty:
                    fon_table_umbrellafundtype = pd.DataFrame()
                else:
                    fetched_data_umbrellafundtype.drop_duplicates(subset=['code', 'UmbrellaFundType'], ignore_index=True, inplace=True)
                    
                    # Print one-line summary for each UmbrellaFundType
                    print("\nIngested Umbrella Fund Types details:")
                    for uft, group in fetched_data_umbrellafundtype.groupby('UmbrellaFundType'):
                        uft_clean = uft.replace('UmbrellaFundType_', '')
                        codes_str = ", ".join(group['code'].unique())
                        out_str = f"Umbrella fund type <{uft_clean}>, Funds: {codes_str}"
                        try:
                            print(out_str)
                        except UnicodeEncodeError:
                            import unicodedata
                            normalized = unicodedata.normalize('NFKD', out_str).encode('ascii', 'ignore').decode('ascii')
                            print(normalized)
                    print()

                    fon_table_umbrellafundtype = fetched_data_umbrellafundtype.pivot_table(index=['code'], columns='UmbrellaFundType', aggfunc='size', fill_value=0)
                    fon_table_umbrellafundtype.reset_index(inplace=True)
                    fon_table_umbrellafundtype = fon_table_umbrellafundtype.map(lambda x: False if x == 0 else (True if x == 1 else x))
                    fon_table_umbrellafundtype.rename(columns={'code': 'symbol'}, inplace=True)
                    print(f"   [+] Processed {fon_table_umbrellafundtype.shape[0]} unique umbrella fund types.")
            except Exception as e:
                fon_table_umbrellafundtype = pd.DataFrame()
                print(f"An error occurred : {e}")
                traceback.print_exc()

            fon_table = pd.merge(fon_table_fundtype, fon_table_umbrellafundtype, on='symbol', how='left')

            # Save to temporary file for Streamlit to display as st.dataframe
            try:
                os.makedirs("data", exist_ok=True)
                fon_table.to_csv("data/last_fon_table.csv", index=False)
            except Exception as e:
                print(f"Warning: Could not save last_fon_table.csv: {e}")

            engine = db_engine()
            if use_postgres and engine is not None:
                try:
                    dtypefon = {"symbol": VARCHAR(3)}
                    fon_table.to_sql(
                        "tefas_funds",
                        engine,
                        if_exists="replace", 
                        index=False , 
                        dtype=dtypefon # type: ignore
                    )
                    print(f"   [+] Successfully saved {fon_table.shape[0]} mutual funds mapping to 'tefas_funds' table.")
                except Exception as e:
                    print(f"An error occurred : {e}")
                    traceback.print_exc()
            engine.dispose()

if __name__ == "__main__":
    main()