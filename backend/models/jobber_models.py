from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Numeric, JSON, Index
from sqlalchemy.orm import relationship
from .base_models import BaseModel

class JobberClient(BaseModel):
    """Jobber client model"""
    __tablename__ = 'jobber_clients'

    jobber_client_id = Column(String(50), unique=True, nullable=False)
    company_name = Column(String(200))
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(200))
    phone = Column(String(50))

    # Address fields
    address_line1 = Column(String(200))
    address_line2 = Column(String(200))
    city = Column(String(100))
    province = Column(String(100))
    postal_code = Column(String(20))
    country = Column(String(100))

    is_active = Column(Boolean, default=True)
    notes = Column(Text)
    tags = Column(JSON)  # Store tags as JSON array

    # Relationships
    jobs = relationship('JobberJob', back_populates='client', cascade='all, delete-orphan')
    invoices = relationship('JobberInvoice', back_populates='client', cascade='all, delete-orphan')

    # Database indexes for webhook performance
    __table_args__ = (
        Index('ix_jobber_clients_jobber_client_id', 'jobber_client_id'),
        Index('ix_jobber_clients_email', 'email'),
        Index('ix_jobber_clients_company_name', 'company_name'),
    )

    @classmethod
    def upsert(cls, jobber_client_id, **kwargs):
        """Create or update a client based on jobber_client_id"""
        from app import db

        client = cls.query.filter_by(jobber_client_id=jobber_client_id).first()

        if client:
            # Update existing client
            for key, value in kwargs.items():
                if hasattr(client, key):
                    setattr(client, key, value)
        else:
            # Create new client
            client = cls(jobber_client_id=jobber_client_id, **kwargs)
            db.session.add(client)

        db.session.commit()
        return client

class JobberJob(BaseModel):
    """Jobber job model"""
    __tablename__ = 'jobber_jobs'

    jobber_job_id = Column(String(50), unique=True, nullable=False)
    client_id = Column(String(50), ForeignKey('jobber_clients.jobber_client_id'), nullable=False)

    title = Column(String(200), nullable=False)
    description = Column(Text)
    status = Column(String(50))  # draft, scheduled, in_progress, completed, cancelled

    # Scheduling
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Financial
    total_amount = Column(Numeric(10, 2))
    currency = Column(String(3), default='USD')

    # Location
    job_address_line1 = Column(String(200))
    job_address_line2 = Column(String(200))
    job_city = Column(String(100))
    job_province = Column(String(100))
    job_postal_code = Column(String(20))
    job_country = Column(String(100))

    # Additional fields
    job_number = Column(String(50))
    tags = Column(JSON)
    custom_fields = Column(JSON)

    # Relationships
    client = relationship('JobberClient', back_populates='jobs')
    invoices = relationship('JobberInvoice', back_populates='job', cascade='all, delete-orphan')

    # Database indexes for webhook performance
    __table_args__ = (
        Index('ix_jobber_jobs_jobber_job_id', 'jobber_job_id'),
        Index('ix_jobber_jobs_client_id', 'client_id'),
        Index('ix_jobber_jobs_status', 'status'),
        Index('ix_jobber_jobs_start_date', 'start_date'),
    )

    @classmethod
    def upsert(cls, jobber_job_id, **kwargs):
        """Create or update a job based on jobber_job_id"""
        from app import db

        job = cls.query.filter_by(jobber_job_id=jobber_job_id).first()

        if job:
            # Update existing job
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
        else:
            # Create new job
            job = cls(jobber_job_id=jobber_job_id, **kwargs)
            db.session.add(job)

        db.session.commit()
        return job

class JobberInvoice(BaseModel):
    """Jobber invoice model"""
    __tablename__ = 'jobber_invoices'

    jobber_invoice_id = Column(String(50), unique=True, nullable=False)
    client_id = Column(String(50), ForeignKey('jobber_clients.jobber_client_id'), nullable=False)
    job_id = Column(String(50), ForeignKey('jobber_jobs.jobber_job_id'))

    invoice_number = Column(String(50))
    status = Column(String(50))  # draft, sent, viewed, paid, overdue, cancelled

    # Financial details
    subtotal = Column(Numeric(10, 2))
    tax_amount = Column(Numeric(10, 2))
    total_amount = Column(Numeric(10, 2))
    currency = Column(String(3), default='USD')

    # Dates
    issue_date = Column(DateTime)
    due_date = Column(DateTime)
    sent_date = Column(DateTime)
    paid_date = Column(DateTime)

    # Payment details
    payment_method = Column(String(50))
    payment_reference = Column(String(100))

    # Additional fields
    notes = Column(Text)
    terms = Column(Text)
    line_items = Column(JSON)  # Store line items as JSON

    # Relationships
    client = relationship('JobberClient', back_populates='invoices')
    job = relationship('JobberJob', back_populates='invoices')

    # Database indexes for webhook performance
    __table_args__ = (
        Index('ix_jobber_invoices_jobber_invoice_id', 'jobber_invoice_id'),
        Index('ix_jobber_invoices_client_id', 'client_id'),
        Index('ix_jobber_invoices_job_id', 'job_id'),
        Index('ix_jobber_invoices_status', 'status'),
        Index('ix_jobber_invoices_due_date', 'due_date'),
    )

    @classmethod
    def upsert(cls, jobber_invoice_id, **kwargs):
        """Create or update an invoice based on jobber_invoice_id"""
        from app import db

        invoice = cls.query.filter_by(jobber_invoice_id=jobber_invoice_id).first()

        if invoice:
            # Update existing invoice
            for key, value in kwargs.items():
                if hasattr(invoice, key):
                    setattr(invoice, key, value)
        else:
            # Create new invoice
            invoice = cls(jobber_invoice_id=jobber_invoice_id, **kwargs)
            db.session.add(invoice)

        db.session.commit()
        return invoice