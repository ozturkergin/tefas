--
-- PostgreSQL database dump
--


-- Dumped from database version 16.10 (Debian 16.10-1.pgdg13+1)
-- Dumped by pg_dump version 16.10 (Debian 16.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: gold_try_rates; Type: TABLE; Schema: public; Owner: ergin
--

CREATE TABLE public.gold_try_rates (
    date date,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision
);


ALTER TABLE public.gold_try_rates OWNER TO tefas;

--
-- Name: tefas; Type: TABLE; Schema: public; Owner: ergin
--

CREATE TABLE public.tefas (
    symbol character varying(3) NOT NULL,
    date date NOT NULL,
    close double precision,
    market_cap double precision,
    number_of_shares double precision,
    number_of_investors double precision
);


ALTER TABLE public.tefas OWNER TO tefas;

--
-- Name: tefas_funds; Type: TABLE; Schema: public; Owner: ergin
--

CREATE TABLE public.tefas_funds (
    title text,
    symbol character varying(3),
    "FundType_Agresif Değişken" boolean,
    "FundType_Alternatif" boolean,
    "FundType_Altın" boolean,
    "FundType_Borçlanma Araçları" boolean,
    "FundType_Borçlanma Araçları Fon Sepeti" boolean,
    "FundType_Dengeli Değişken" boolean,
    "FundType_Değişken" boolean,
    "FundType_Diğer Fon Sepeti" boolean,
    "FundType_Döviz" boolean,
    "FundType_Döviz Cinsinden İhraç (Dolar)" boolean,
    "FundType_Döviz Cinsinden İhraç (Euro)" boolean,
    "FundType_Döviz Cinsinden İhraç (Pound)" boolean,
    "FundType_Emtia" boolean,
    "FundType_Endeks" boolean,
    "FundType_Endeks Hisse Senedi" boolean,
    "FundType_Eurobond" boolean,
    "FundType_Fon Sepeti" boolean,
    "FundType_Gümüş" boolean,
    "FundType_Hisse Senedi" boolean,
    "FundType_Hisse Senedi Yoğun" boolean,
    "FundType_Karma" boolean,
    "FundType_Katılım" boolean,
    "FundType_Kira Sertifikaları" boolean,
    "FundType_Kısa Vadeli" boolean,
    "FundType_Kısa Vadeli Borçlanma Araçları" boolean,
    "FundType_Kıymetli Madenler" boolean,
    "FundType_Mutlak Getiri Hedefli" boolean,
    "FundType_Orta Vadeli" boolean,
    "FundType_Para Piyasası" boolean,
    "FundType_Sektör" boolean,
    "FundType_Serbest" boolean,
    "FundType_Sürdürülebilirlik Fonları" boolean,
    "FundType_Uzun Vadeli" boolean,
    "FundType_Uzun Vadeli Borçlanma Araçları" boolean,
    "FundType_Yabancı" boolean,
    "FundType_Yabancı Fon Sepeti" boolean,
    "FundType_Çalışanlarına Yönelik" boolean,
    "FundType_Çoklu Varlık" boolean,
    "FundType_Özel" boolean,
    "FundType_İştirak" boolean,
    symbolwithtitle text,
    "UmbrellaFundType_Borçlanma Araçları Şemsiye Fonu" boolean,
    "UmbrellaFundType_Değişken Şemsiye Fonu" boolean,
    "UmbrellaFundType_Fon Sepeti Şemsiye Fonu" boolean,
    "UmbrellaFundType_Hisse Senedi Şemsiye Fonu" boolean,
    "UmbrellaFundType_Karma Şemsiye Fonu" boolean,
    "UmbrellaFundType_Katılım Şemsiye Fonu" boolean,
    "UmbrellaFundType_Kıymetli Madenler Şemsiye Fonu" boolean,
    "UmbrellaFundType_Para Piyasası Şemsiye Fonu" boolean,
    "UmbrellaFundType_Serbest Şemsiye Fonu" boolean
);


ALTER TABLE public.tefas_funds OWNER TO tefas;

--
-- Name: tefas_transformed; Type: TABLE; Schema: public; Owner: ergin
--

CREATE TABLE public.tefas_transformed (
    date date NOT NULL,
    symbol character varying(3) NOT NULL,
    close double precision,
    market_cap double precision,
    number_of_shares double precision,
    number_of_investors double precision,
    year integer,
    week_no text,
    year_week text,
    day_of_week text,
    market_cap_per_investors double precision,
    open double precision,
    high double precision,
    low double precision,
    close_7d double precision,
    market_cap_7d double precision,
    number_of_shares_7d double precision,
    number_of_investors_7d double precision,
    market_cap_per_investors_7d double precision,
    close_1m double precision,
    market_cap_1m double precision,
    number_of_shares_1m double precision,
    number_of_investors_1m double precision,
    market_cap_per_investors_1m double precision,
    close_3m double precision,
    market_cap_3m double precision,
    number_of_shares_3m double precision,
    number_of_investors_3m double precision,
    market_cap_per_investors_3m double precision,
    close_6m double precision,
    market_cap_6m double precision,
    number_of_shares_6m double precision,
    number_of_investors_6m double precision,
    market_cap_per_investors_6m double precision,
    close_1y double precision,
    market_cap_1y double precision,
    number_of_shares_1y double precision,
    number_of_investors_1y double precision,
    market_cap_per_investors_1y double precision,
    close_3y double precision,
    market_cap_3y double precision,
    number_of_shares_3y double precision,
    number_of_investors_3y double precision,
    market_cap_per_investors_3y double precision,
    "EMA_5" double precision,
    "EMA_10" double precision,
    "EMA_12" double precision,
    "EMA_20" double precision,
    "EMA_26" double precision,
    "EMA_50" double precision,
    "EMA_100" double precision,
    "EMA_200" double precision,
    "SMA_5" double precision,
    "RSI_14" double precision,
    "MACD" double precision
);


ALTER TABLE public.tefas_transformed OWNER TO tefas;

--
-- Name: usd_try_rates; Type: TABLE; Schema: public; Owner: ergin
--

CREATE TABLE public.usd_try_rates (
    date date,
    open double precision,
    high double precision,
    low double precision,
    close double precision,
    volume double precision
);


ALTER TABLE public.usd_try_rates OWNER TO tefas;

--
-- Name: youtube; Type: TABLE; Schema: public; Owner: ergin
--

CREATE TABLE public.youtube (
    "videoId" character varying(20) NOT NULL,
    title text,
    "channelTitle" text,
    transcript text,
    "publishedAt" timestamp with time zone
);


ALTER TABLE public.youtube OWNER TO tefas;

--
-- Name: tefas tefas_pkey; Type: CONSTRAINT; Schema: public; Owner: ergin
--

ALTER TABLE ONLY public.tefas
    ADD CONSTRAINT tefas_pkey PRIMARY KEY (symbol, date);


--
-- Name: tefas_transformed tefas_transformed_pkey; Type: CONSTRAINT; Schema: public; Owner: ergin
--

ALTER TABLE ONLY public.tefas_transformed
    ADD CONSTRAINT tefas_transformed_pkey PRIMARY KEY (symbol, date);

