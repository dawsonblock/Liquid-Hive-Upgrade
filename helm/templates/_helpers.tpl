{{- define "liquid-hive-upgrade.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "liquid-hive-upgrade.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "liquid-hive-upgrade.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version -}}
{{- end -}}