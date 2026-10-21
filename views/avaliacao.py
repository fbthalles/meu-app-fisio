from services.session_resilience import (
    injetar_wake_lock_mobile,
    inicializar_estado_avaliacao,
    monitor_autosave_firestore,
)

# No início da função render_avaliacao(db, paciente_id):
injetar_wake_lock_mobile()
inicializar_estado_avaliacao(avaliacao_id=f"draft_{paciente_id}", db_client=db)
monitor_autosave_firestore(db_client=db)
