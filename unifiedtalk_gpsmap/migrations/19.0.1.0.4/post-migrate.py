def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_config_parameter
           SET value = CASE value
               WHEN 'open' THEN 'enterprise'
               WHEN 'permitted' THEN 'limited'
               ELSE value
           END
         WHERE key = 'unifiedtalk_gpsmap.registration_type'
           AND value IN ('open', 'permitted')
        """
    )
