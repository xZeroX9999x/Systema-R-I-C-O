def get_db_connection() -> sqlite3.Connection:
    """Obtiene conexión a la base de datos SQLite con manejo seguro de rutas."""
    settings = load_settings()
    db_path = settings['DB_PATH']
    
    # Garantizar que el directorio padre exista
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Directorio de DB creado: {db_dir}")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")  # Mejor concurrencia
        return conn
    except sqlite3.Error as e:
        logger.error(f"Error crítico conectando a SQLite: {e}")
        raise RuntimeError(f"No se pudo inicializar la base de datos en {db_path}") from e
