import pandas as pd
from typing import List, Optional
from datetime import datetime
from services.firebase_service import FirebaseService
from models.patient import Patient
from utils.logger import AppLogger
from utils.validators import Validators

logger_module = "patient_service"

class PatientService:
    """Serviço de negócio para operações com Pacientes."""
    
    def __init__(self):
        self.firebase = FirebaseService()
        self.collection_name = "Cadastro"
    
    def get_all_patients(self) -> List[Patient]:
        """Retorna todos os pacientes."""
        try:
            df = self.firebase.read_collection(self.collection_name)
            
            if df.empty:
                AppLogger.warning(logger_module, "Nenhum paciente encontrado")
                return []
            
            patients = [Patient.from_dict(row.to_dict()) for _, row in df.iterrows()]
            AppLogger.info(logger_module, f"Recuperados {len(patients)} pacientes")
            return patients
            
        except Exception as e:
            AppLogger.error(logger_module, "Erro ao recuperar pacientes", exception=e)
            return []
    
    def get_patient_by_name(self, name: str) -> Optional[Patient]:
        """Busca paciente por nome."""
        try:
            if not Validators.validate_required_field(name, "Nome do Paciente"):
                return None
            
            df = self.firebase.read_by_filter(
                self.collection_name,
                "Nome",
                "==",
                name.strip()
            )
            
            if df.empty:
                AppLogger.warning(logger_module, f"Paciente não encontrado: {name}")
                return None
            
            patient_data = df.iloc[0].to_dict()
            patient = Patient.from_dict(patient_data)
            AppLogger.info(logger_module, f"Paciente encontrado: {name}")
            return patient
            
        except Exception as e:
            AppLogger.error(logger_module, f"Erro ao buscar paciente {name}", exception=e)
            return None
    
    def create_patient(
        self,
        name: str,
        birth_date: str,
        cpf: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        city_state: Optional[str] = None,
        occupation: Optional[str] = None,
        clinical_diagnosis: Optional[str] = None
    ) -> bool:
        """Cria novo paciente com validação."""
        try:
            if not Validators.validate_patient_name(name):
                return False
            
            if not Validators.validate_date(birth_date):
                AppLogger.warning(logger_module, f"Data inválida: {birth_date}")
                return False
            
            if email and not Validators.validate_email(email):
                return False
            
            patient_data = {
                "Nome": name.strip(),
                "Data_Nascimento": birth_date,
                "CPF": cpf or "",
                "Telefone": phone or "",
                "Email": email or "",
                "Cidade_Estado": city_state or "",
                "Ocupacao": occupation or "",
                "Diagnostico_Clinico": clinical_diagnosis or "",
                "Historia": "",
                "Criado_em": datetime.now().isoformat()
            }
            
            doc_id = self.firebase.create(self.collection_name, patient_data)
            
            if doc_id:
                AppLogger.info(logger_module, f"Paciente criado com sucesso: {name}")
                return True
            else:
                AppLogger.error(logger_module, f"Falha ao criar paciente: {name}")
                return False
                
        except Exception as e:
            AppLogger.error(logger_module, "Erro ao criar paciente", exception=e)
            return False
    
    def get_patient_names_list(self) -> List[str]:
        """Retorna lista de nomes de todos os pacientes."""
        try:
            df = self.firebase.read_collection(self.collection_name, use_cache=True)
            
            if df.empty or "Nome" not in df.columns:
                return []
            
            names = sorted(df["Nome"].dropna().unique().tolist())
            return names
            
        except Exception as e:
            AppLogger.error(logger_module, "Erro ao recuperar lista de nomes", exception=e)
            return []
