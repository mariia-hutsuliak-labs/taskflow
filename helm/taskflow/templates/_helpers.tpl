{{/*
Коротке ім'я чарта.
*/}}
{{- define "taskflow.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Повне ім'я об'єктів: <реліз>-<чарт>. Якщо ім'я релізу вже містить ім'я чарта
(наприклад, реліз "taskflow"), повторення не додається.
Саме від нього будуються імена всіх об'єктів, тому чарт можна встановити
двічі в один кластер під різними іменами релізу.
*/}}
{{- define "taskflow.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Назва і версія чарта для мітки helm.sh/chart.
*/}}
{{- define "taskflow.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Мітки-селектори (незмінні протягом життя об'єкта).
Мітку компонента (backend, db, ...) кожен маніфест додає сам.
*/}}
{{- define "taskflow.selectorLabels" -}}
app.kubernetes.io/name: {{ include "taskflow.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Повний набір міток для всіх об'єктів.
*/}}
{{- define "taskflow.labels" -}}
helm.sh/chart: {{ include "taskflow.chart" . }}
{{ include "taskflow.selectorLabels" . }}
app.kubernetes.io/part-of: taskflow
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
