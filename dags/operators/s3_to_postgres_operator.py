from airflow.models.baseoperator import BaseOperator
from airflow.utils.decorators import apply_defaults
from airflow.hooks.S3_hook import S3Hook
from airflow.hooks.postgres_hook import PostgresHook

import json


class S3ToPostgresOperator(BaseOperator):
	""" 
	Collects data from a file hosted on AWS S3 and loads it into a Postgres table. 
	Current version requires JSON input and a pre-defined data model.
	
	:param s3_conn_id:			S3 Connection ID
	:param s3_bucket:			S3 Bucket Destination
	:param s3_prefix:			S3 File Prefix
	:param source_data_type:	S3 Source File data type
	:param postgres_conn_id: 	Postgres Connection ID
	:param db_schema:			Postgres Target Schema
	:param db_table:			Postgres Target Table
	:param get_latest:			if True, pulls data last modified file in S3 path
	"""
	
	@apply_defaults
	def __init__(self,
		s3_conn_id=None,
		s3_bucket=None,
		s3_prefix='',
		source_data_type='',
		postgres_conn_id='postgres_default',
		schema='public',
		table='raw_load',
		get_latest=False,		
		*args, 
		**kwargs) -> None: 
		
		super().__init__(*args, **kwargs)
		
		self.s3_conn_id = s3_conn_id
		self.s3_bucket = s3_bucket
		self.s3_prefix = s3_prefix
		self.source_data_type = source_data_type
		self.postgres_conn_id = postgres_conn_id
		self.schema = schema,
		self.table = table,
		self.get_latest = get_latest
	
	
	def execute(self, context):
		"""
		Executes the operator, including running a max filesize check if enabled. 
		"""
		s3_hook = S3Hook(self.s3_conn_id)
		s3_session = s3_hook.get_session()
		s3_client = s3_session.client('s3')
		
		if self.get_latest == True:
			objects = s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=self.s3_prefix)['Contents']
			latest = max(objects, key=lambda x: x['LastModified'])
			s3_obj = s3_client.get_object(Bucket=self.s3_bucket, Key=latest['Key'])
			
		file_content = s3_obj['Body'].read().decode('utf-8')
		json_content = json.loads(file_content)		
		
		pg_hook = PostgresHook(self.postgres_conn_id)
		pg_conn = pg_hook.get_conn()
		cur = pg_conn.cursor()
		
		if isinstance(self.schema, tuple):
			schema = self.schema[0]
		else:
			schema = self.schema
		if isinstance(self.table, tuple):
			table = self.table[0]
		else:
			table = self.table
		
		print('inserting...')
		
		pg_hook.insert_rows(f'{schema}.{table}', ['1','2','3'])
		
		
		cur.executemany(f"""
			INSERT INTO {schema}.{table}(
				raw_id,
				created_at,
				updated_at,
				eviction_id,
				address,
				city,
				state,
				zip,
				file_date,
				non_payment,
				breach,
				nuisance,
				illegal_use,
				failure_to_sign_renewal,
				access_denial,
				unapproved_subtenant,
				owner_move_in,
				demolition,
				capital_improvement,
				substantial_rehab,
				ellis_act_withdrawal,
				condo_conversion,
				roommate_same_unit,
				other_cause,
				late_payments,
				lead_remediation,
				development,
				good_samaritan_ends,
				constraints_date,
				supervisor_district,
				neighborhood
			)
			VALUES(
				%(:id)s, %(:created_at)s, %(:updated_at)s, %(eviction_id)s, %(address)s, %(city)s, %(state)s, %(zip)s,
				%(file_date)s, %(non_payment)s, %(breach)s, %(nuisance)s, %(illegal_use)s, %(failure_to_sign_renewal)s,
				%(access_denial)s, %(unapproved_subtenant)s, %(owner_move_in)s, %(demolition)s, %(capital_improvement)s,
				%(substantial_rehab)s, %(ellis_act_withdrawal)s, %(condo_conversion)s, %(roommate_same_unit)s,
				%(other_cause)s, %(late_payments)s, %(lead_remediation)s, %(development)s, %(good_samaritan_ends)s,
				%(constraints_date)s, %(supervisor_district)s, %(neighborhood)s
			);
		""",({
			':id': line[':id'],
			':created_at': line[':created_at'],
			':updated_at': line[':updated_at'],
			'eviction_id': line['eviction_id'],
			'address': line.get('address', None),
			'city': line.get('city', None),
			'state': line.get('state', None),
			'zip': line.get('zip', None),
			'file_date': line.get('file_date', None),
			'non_payment': line.get('non_payment', None),
			'breach': line.get('breach', None),
			'nuisance': line.get('nuisance', None),
			'illegal_use': line.get('illegal_use', None),
			'failure_to_sign_renewal': line.get('failure_to_sign_renewal', None),
			'access_denial': line.get('access_denial', None),
			'unapproved_subtenant': line.get('unapproved_subtenant', None),
			'owner_move_in': line.get('owner_move_in', None),
			'demolition': line.get('demolition', None),
			'capital_improvement': line.get('capital_improvement', None),
			'substantial_rehab': line.get('substantial_rehab', None),
			'ellis_act_withdrawal': line.get('ellis_act_withdrawal', None),
			'condo_conversion': line.get('condo_conversion', None),
			'roommate_same_unit': line.get('roommate_same_unit', None),
			'other_cause': line.get('other_cause', None),
			'late_payments': line.get('late_payments', None),
			'lead_remediation': line.get('lead_remediation', None),
			'development': line.get('development', None),
			'good_samaritan_ends': line.get('good_samaritan_ends', None),
			'constraints_date': line.get('constraints_date', None),
			'supervisor_district': line.get('supervisor_district', None),
			'neighborhood': line.get('neighborhood', None)
		} for line in json_content))
		
		print('inserting complete...')
		
		pg_conn.commit()
		cur.close()