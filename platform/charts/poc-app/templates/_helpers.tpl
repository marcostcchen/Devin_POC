{{- define "poc-app.name" -}}
{{ .Values.project.id }}
{{- end -}}

{{- define "poc-app.labels" -}}
app.kubernetes.io/name: {{ .Values.project.id }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
poc.platform/project: {{ .Values.project.id }}
poc.platform/stage: {{ .Values.project.stage }}
poc.platform/data-classification: {{ .Values.data.classification }}
{{- end -}}

{{- define "poc-app.selectorLabels" -}}
app.kubernetes.io/name: {{ .Values.project.id }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
