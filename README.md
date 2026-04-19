# R-I-C-O Bot v4.0

Sistema autónomo de análisis de portafolio con **lógica dual**: buy-and-hold para ETFs diversificados + tácticas técnicas para acciones individuales. Ejecuta semanalmente en GitHub Actions y envía un reporte HTML por correo.

## Filosofía

La versión anterior (v3.0) trataba a todos los activos con las mismas reglas: RSI alto → vender, RSI bajo → comprar. Esto destruye valor en ETFs globales porque:

- **Dalbar 2024**: el inversor promedio que intenta hacer market timing pierde ~8% anual vs buy-and-hold.
- **J.P. Morgan**: perderse los 30 mejores días del mercado en los últimos 20 años reduce el retorno un 84%.
- **Evidencia**: los índices con 9.000+ acciones tienen deriva alcista estructural; el RSI solo funciona bien como señal de reversión en activos individuales con comportamiento mean-reverting.

v4.0 separa la lógica:

| Tipo de activo | Lógica | Decisión de compra | Decisión de venta |
|----------------|--------|---------------------|-------------------|
| **ETFs diversificados** (VT, ITOT) | Largo plazo | DCA mensual fijo (30k CLP) al que tenga mejor momentum 6m/12m | **Nunca por RSI**. Solo circuit breaker si RSI mensual ≥80 **Y** precio ≥25% sobre MA200 |
| **Acciones individuales** (NVDA, IBIT, CGW, TTWO) | Táctico | RSI ≤60 + momentum 3m ≥-10% + sobre MA200 + volumen sano | RSI ≥72 (fases 25/35/50%) o trailing stop ≥15% |

## Estructura del proyecto

```
rico-bot-v4/
├── .github/
│   └── workflows/
│       └── rico-bot.yml       # Cron semanal en GitHub Actions
├── rico_bot.py                # Script principal (9 módulos)
├── requirements.txt           # yfinance + numpy
└── README.md                  # Este archivo
```

## Módulos del script

| # | Módulo | Responsabilidad |
|---|--------|------------------|
| 1 | Configuración | Tickers, presupuesto, umbrales, credenciales email |
| 2 | Análisis técnico | RSI (diario/semanal/mensual), momentum N meses, MA, volumen |
| 3 | USD/CLP | Tipo de cambio vía Yahoo Finance con fallback |
| 4 | `analizar_etf()` | Ranking por momentum — nunca vende por RSI |
| 5 | `analizar_accion()` | RSI + filtro anti-cuchillo + trailing stop |
| 6 | Régimen de mercado | Modo cautela inteligente (2+ señales reales) |
| 7 | Motor de decisión | Asignación mensual del presupuesto |
| 8 | Generador HTML | Email con alertas, asignación y detalle por activo |
| 9 | Email + log + main | Envío SMTP + CSV histórico |

## Presupuesto mensual (50.000 CLP)

| Destino | Monto base | % |
|---------|-----------|---|
| ETF (DCA) | 30.000 CLP | 60% |
| Acciones top 1 | 12.500 CLP | 25% |
| Acciones top 2 | 5.000 CLP | 10% |
| Reserva cash | 2.500 CLP | 5% |

El 60% al ETF es el cambio más importante vs v3.0 (antes era 30%): duplica lo que va al núcleo diversificado que construye patrimonio a 10-20 años.

## Parámetros clave (ajustables en `rico_bot.py`)

### ETFs (largo plazo)
- `ETF_PAUSA_RSI_MENSUAL = 80` — Umbral de burbuja
- `ETF_PAUSA_DIST_MA200_PCT = 25` — Extensión extrema sobre MA200
- `ETF_MOMENTUM_CORTO_MESES = 6` — Ventana momentum corto
- `ETF_MOMENTUM_LARGO_MESES = 12` — Ventana momentum largo

### Acciones (táctico)
- `ACCION_RSI_MAX_COMPRA = 60` — RSI máximo para comprar
- `ACCION_MOMENTUM_MIN_3M = -10` — Filtro anti-cuchillo
- `ACCION_TRAILING_STOP_PCT = 15` — Protección capital
- `ACCION_VENTA_FASES` — RSI 72/78/85 → vender 25/35/50%

### Régimen de mercado
- `MERCADO_ALERTA_VT_RSI_SEMANAL = 78`
- `MERCADO_ALERTA_VOLATILIDAD = 35`
- `MERCADO_ALERTA_DIST_MA200_PCT = 20`
- Requiere **2 de 3** señales para activar modo cautela

## Instalación y uso

### 1. Subir a GitHub
```bash
git init
git add .
git commit -m "R-I-C-O Bot v4.0"
git remote add origin https://github.com/<tu-usuario>/<tu-repo>.git
git branch -M main
git push -u origin main
```

### 2. Configurar secrets en GitHub
Ve a **Settings → Secrets and variables → Actions → New repository secret** y añade:

| Secret | Valor |
|--------|-------|
| `EMAIL_DESTINO` | Tu email donde recibes el reporte |
| `EMAIL_USUARIO` | Email desde el que se envía (tu Gmail) |
| `EMAIL_PASSWORD` | [App Password de Gmail](https://myaccount.google.com/apppasswords) (no tu contraseña normal) |
| `SMTP_SERVER` | `smtp.gmail.com` (opcional, es el default) |
| `SMTP_PORT` | `587` (opcional, es el default) |

### 3. Ejecutar manualmente (primera prueba)
Ve a **Actions → R-I-C-O Bot v4.0 → Run workflow**. Debería llegar un email con el primer reporte.

### 4. El cron se activa automáticamente
Ejecuta cada sábado a las 14:00 UTC (~11:00 hora Chile en verano).

## Migrar desde v3.0

Si vienes del v3.0, el CSV histórico tiene columnas diferentes. Dos opciones:

**Opción A (limpio)**: borra `historico_decisiones.csv` antes del primer run de v4.0.
```bash
rm historico_decisiones.csv
```

**Opción B (conservar histórico)**: renombra el viejo.
```bash
mv historico_decisiones.csv historico_decisiones_v3.csv
```

## Personalización

### Cambiar activos
Edita en `rico_bot.py`:
```python
ETFS_CORE = ["VT", "ITOT"]
ACCIONES_TACTICAS = ["NVDA", "IBIT", "CGW", "TTWO"]
```

### Cambiar presupuesto
```python
PRESUPUESTO_MENSUAL = 50000
APORTE_ETF_MENSUAL      = 30000
APORTE_ACCIONES_MENSUAL = 17500
APORTE_CASH_MENSUAL     = 2500
```

### Cambiar frecuencia
En `.github/workflows/rico-bot.yml`, ajusta el cron:
- Diario: `'0 14 * * *'`
- Lunes y jueves: `'0 14 * * 1,4'`
- [Crontab guru](https://crontab.guru/) para más combinaciones

## Limitaciones conocidas

- **No considera impuestos chilenos**: en Chile, las ganancias de capital en acciones/ETFs extranjeros pueden tributar Impuesto Global Complementario. Vender seguido genera obligaciones.
- **No incluye comisiones de corretaje**: a 50.000 CLP mensuales, las comisiones pesan. Considera corredoras de bajo costo (Fintual, Racional).
- **No hay renta fija**: el portafolio es 100% renta variable. Para rebalancear de verdad considera agregar un ETF de bonos (BND, AGG).

## Disclaimer

Esto **no es asesoría financiera**. Es un sistema automatizado de alertas basado en reglas mecánicas, que puede equivocarse. Antes de actuar sobre cualquier señal, contrasta con tu criterio y contexto personal (impuestos, liquidez, objetivos, horizonte).

## Licencia

MIT — úsalo, modifícalo, compártelo.
