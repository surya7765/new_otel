apm-server:
  host: "apm-server:8200"
setup.template.settings:
  index:
    number_of_shards: 1
    codec: best_compression
setup.kibana:
  host: "kibana:5601"
  username: "elastic"
  password: "elastic"
output.elasticsearch:
  hosts: ["http://elasticsearch:9200"]
  username: "elastic"
  password: "elastic"
indices:
  - index: "apm-%{[beat.version]}-sourcemap"
    when.contains:
      processor.event: "sourcemap"
  - index: "apm-%{[beat.version]}-error-%{+yyyy.MM.dd}"
    when.contains:
      processor.event: "error"
  - index: "apm-%{[beat.version]}-transaction-%{+yyyy.MM.dd}"
    when.contains:
      processor.event: "transaction"
  - index: "apm-%{[beat.version]}-span-%{+yyyy.MM.dd}"
    when.contains:
      processor.event: "span"
