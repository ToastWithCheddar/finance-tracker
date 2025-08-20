from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import mapped_column, Mapped
from .base import BaseModel
from typing import Optional

class MLModelPerformance(BaseModel):
    __tablename__ = "ml_model_performance"
    
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    accuracy: Mapped[Optional[float]] = mapped_column(Float)
    precision: Mapped[Optional[float]] = mapped_column(Float)
    recall: Mapped[Optional[float]] = mapped_column(Float)
    f1_score: Mapped[Optional[float]] = mapped_column(Float)
    training_data_size: Mapped[Optional[int]] = mapped_column(Integer)
    
    def __repr__(self):
        return f"<MLModelPerformance(id={self.id}, model_name='{self.model_name}', version='{self.version}', accuracy={self.accuracy})>"