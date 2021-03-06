# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SendGroup'
        db.create_table('api_sendgroup', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('api', ['SendGroup'])

        # Adding model 'SentSMS'
        db.create_table('api_sentsms', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('send_group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.SendGroup'], null=True, blank=True)),
            ('to_msisdn', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('from_msisdn', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('charset', self.gf('django.db.models.fields.CharField')(default='utf8', max_length=32, blank=True)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=160)),
            ('transport_name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('transport_msg_id', self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True)),
            ('transport_status', self.gf('django.db.models.fields.CharField')(default='', max_length=256, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('delivered_at', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('api', ['SentSMS'])

        # Adding model 'SMPPLink'
        db.create_table('api_smpplink', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sent_sms', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.SentSMS'], unique=True)),
            ('sequence_number', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('api', ['SMPPLink'])

        # Adding model 'SMPPResp'
        db.create_table('api_smppresp', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('sent_sms', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.SentSMS'], unique=True)),
            ('sequence_number', self.gf('django.db.models.fields.IntegerField')()),
            ('command_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('command_status', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('message_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('api', ['SMPPResp'])

        # Adding model 'ReceivedSMS'
        db.create_table('api_receivedsms', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('to_msisdn', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('from_msisdn', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('charset', self.gf('django.db.models.fields.CharField')(default='utf8', max_length=32, blank=True)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=160)),
            ('transport_name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('transport_msg_id', self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True)),
            ('received_at', self.gf('django.db.models.fields.DateTimeField')()),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('api', ['ReceivedSMS'])

        # Adding model 'Profile'
        db.create_table('api_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('api', ['Profile'])

        # Adding model 'URLCallback'
        db.create_table('api_urlcallback', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('profile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Profile'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('url', self.gf('vumi.webapp.api.fields.AuthenticatedURLField')(max_length=200, blank=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('api', ['URLCallback'])


    def backwards(self, orm):
        
        # Deleting model 'SendGroup'
        db.delete_table('api_sendgroup')

        # Deleting model 'SentSMS'
        db.delete_table('api_sentsms')

        # Deleting model 'SMPPLink'
        db.delete_table('api_smpplink')

        # Deleting model 'SMPPResp'
        db.delete_table('api_smppresp')

        # Deleting model 'ReceivedSMS'
        db.delete_table('api_receivedsms')

        # Deleting model 'Profile'
        db.delete_table('api_profile')

        # Deleting model 'URLCallback'
        db.delete_table('api_urlcallback')


    models = {
        'api.profile': {
            'Meta': {'object_name': 'Profile'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'api.receivedsms': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'ReceivedSMS'},
            'charset': ('django.db.models.fields.CharField', [], {'default': "'utf8'", 'max_length': '32', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_msisdn': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '160'}),
            'received_at': ('django.db.models.fields.DateTimeField', [], {}),
            'to_msisdn': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'transport_msg_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'transport_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'api.sendgroup': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'SendGroup'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'api.sentsms': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'SentSMS'},
            'charset': ('django.db.models.fields.CharField', [], {'default': "'utf8'", 'max_length': '32', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'delivered_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'from_msisdn': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '160'}),
            'send_group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['api.SendGroup']", 'null': 'True', 'blank': 'True'}),
            'to_msisdn': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'transport_msg_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'transport_name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'transport_status': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '256', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'api.smpplink': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'SMPPLink'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sent_sms': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['api.SentSMS']", 'unique': 'True'}),
            'sequence_number': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'api.smppresp': {
            'Meta': {'ordering': "['-created_at']", 'object_name': 'SMPPResp'},
            'command_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'command_status': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'sent_sms': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['api.SentSMS']", 'unique': 'True'}),
            'sequence_number': ('django.db.models.fields.IntegerField', [], {}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'api.urlcallback': {
            'Meta': {'object_name': 'URLCallback'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['api.Profile']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'url': ('vumi.webapp.api.fields.AuthenticatedURLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['api']
