# regras-operativas-service

Serviço para aplicação de regras operativas em casos de NEWAVE / DECOMP / DESSEM mediante a evolução de estudos. Este serviço é fornecido por meio de uma API REST contendo uma única rota, que recebe os argumentos necessários para realizar a aplicação de regras operativas do tipo armazenamento-vazão.

Atualmente é esperado que este serviço seja lançado no próprio cluster, com acesso ao sistema de arquivos onde os casos que serão processados se encontram. Além disso, para regras do tipo armazenamento-vazão, é necessária uma prospecção futura dos armazenamentos do caso ao qual serão aplicadas as regras, que hoje é fornecido através do resultado de outros casos, presumidamente anteriores ao caso em questão, na própria rota provida pelo serviço.

## Instalação

Para realizar a instalação a partir do repositório, é recomendado criar um ambiente virtual e realizar a instalação das dependências dentro do mesmo.

```
$ git clone https://github.com/rjmalves/regras-operativas-service
$ cd regras-operativas-service
$ python3 -m venv ./venv
$ source ./venv/bin/activate
$ pip install -r requirements.txt
```

## Configuração

A configuração do serviço pode ser feita através de um arquivo de variáveis de ambiente `.env`, existente no próprio diretório de instalação. O conteúdo deste arquivo:

```
CLUSTER_ID=1
HOST="0.0.0.0"
PORT=5054
ROOT_PATH="/api/v1/rules"
```

Cada deploy do `regras-operativas-service` deve ter um atributo `CLUSTER_ID` único, para que outros serviços possam controlar atividades em clusters distintos. 

Atualmente as opções suportadas são:

|       Campo       |   Valores aceitos   |
| ----------------- | ------------------- |
| CLUSTER_ID        | `int`               |
| HOST              | `str`               |
| PORT              | `int`               |
| ROOT_PATH         | `str` (URL prefix)  |


## Uso

Para executar o programa, basta interpretar o arquivo `main.py`:

```
$ source ./venv/bin/activate
$ python main.py
```

No terminal é impresso um log de acompanhamento:

```
INFO:     Started server process [2133]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:5043 (Press CTRL+C to quit)
INFO:     127.0.0.1:36872 - "GET /docs HTTP/1.1" 200 OK
INFO:     127.0.0.1:36872 - "GET /openapi.json HTTP/1.1" 200 OK
```


Maiores detalhes sobre a rota disponível pode ser visto ao lançar a aplicação localmente e acessar a rota `/docs`, que possui uma página no formato [OpenAPI](https://swagger.io/specification/). Em geral, casos são referenciados por meio de seus caminhos no sistema de arquivos codificados em `base62` e as regras operativas são modeladas pelo objeto `ReservoirRule`, que possui as especificações:

```json
    {
        "reservoirCode": 0,
        "uheCode": 0,
        "constraintType": "string",
        "month": 0,
        "minVolume": 0,
        "maxVolume": 0,
        "minLimit": 0,
        "maxLimit": 0,
        "frequency": "string",
        "label": "string"
    }
```

## Definição de Regra Operativa

As regras operativas suportadas por este serviço são do tipo armazenamento-vazão. Isto é, cada regra se define com as propriedades:

 - `reservoirCode`: código do reservatório cujo volume armazenado define a faixa de operação da usina
 - `uheCode`: código da usina hidrelétrica cuja operação é influenciada pelo reservatório
 - `constraintType`: variável que é influenciada (atualmente suporta QDEF ou QTUR)
 - `month`: mês de vigência da regra, visto que na prática muitas regras são sazonalizadas no ano (1 - 12)
 - `minVolume`: limite inferior da faixa de volume para ativação da regra (%)
 - `maxVolume`: limite superior da faixa de volume para ativação da regra (%)
 - `minLimit`: limite inferior da variável influenciada (m3/s)
 - `maxLimit`: limite superior da variável influenciada (m3/s)
 - `frequency`: frequência de atualização da regra (atualmente suporta S - semanal e M - mensal)
 - `label`: rótulo da faixa de operação definida pela regra (normal, atenção, restrição, etc., apenas informativo)

Um exemplo de regras válidas, para a UHE Três Marias (156) no mês de Janeiro, já utilizadas:

```json
[
    {
        "reservoirCode": 156,
        "uheCode": 156,
        "constraintType": "QDEF",
        "month": 1,
        "minVolume": 0.0,
        "maxVolume": 30.0,
        "minLimit": 100.0,
        "maxLimit": 99999.0,
        "frequency": "M",
        "label": "Restricao"
    },
    {
        "reservoirCode": 156,
        "uheCode": 156,
        "constraintType": "QTUR",
        "month": 1,
        "minVolume": 0.0,
        "maxVolume": 30.0,
        "minLimit": 0.0,
        "maxLimit": 150.0,
        "frequency": "M",
        "label": "Restricao"
    }
]
```

Estas regras definidas acima modelam o comportamento desejado para a UHE Três Marias nos meses de Janeiro, segundo a Resolução ANA nº 70 para a Bacia do Rio São Francisco. É realizada uma limitação da defluência mínima da usina em 100 m3/s e do turbinamento máximo em 150 m3/s, sempre que o reservatório se encontrar entre 0% e 30% do volume útil.

## Regras de Reservatórios Equivalentes

Uma determinada variável de operação de uma usina pode ser determinada não apenas a partir de um reservatório, mas a partir do armazenamento total de um conjunto de reservatórios, o que é chamado de reservatório equivalente. Desta forma, é suportada a definição de mais de uma regra que atua em uma determinada usina no mesmo mês, na mesma variável e com a mesma periodicidade, tomando como base diferentes reservatórios.

O serviço irá construir uma regra de reservatório equivalente a partir das regras informadas, agrupando todas as regras com os mesmos `uheCode`, `constaintType`, `month`, `frequency` e `label`. Repare que, para este caso, é importante que cada faixa de operação da usina tenha um label diferente, e que regras de reservatórios que compõe um reservatório equivalente tenham `labels` compatíveis.

Um exemplo de regras equivalentes é para a defluência da usina de Jupiá (45), que pode ser determinada com base em um reservatório equivalente construído com usinas da bacia do Grande. Para o mês de janeiro, por exemplo, na faixa de restrição:


```json
[
    {
        "reservoirCode": 6,
        "uheCode": 45,
        "constraintType": "QDEF",
        "month": 1,
        "minVolume": 0.0,
        "maxVolume": 30.0,
        "minLimit": 0.0,
        "maxLimit": 2700.0,
        "frequency": "S",
        "label": "Restricao"
    },
    {
        "reservoirCode": 24,
        "uheCode": 45,
        "constraintType": "QDEF",
        "month": 1,
        "minVolume": 0.0,
        "maxVolume": 30.0,
        "minLimit": 0.0,
        "maxLimit": 2700.0,
        "frequency": "S",
        "label": "Restricao"
    },
    {
        "reservoirCode": 25,
        "uheCode": 45,
        "constraintType": "QDEF",
        "month": 1,
        "minVolume": 0.0,
        "maxVolume": 30.0,
        "minLimit": 0.0,
        "maxLimit": 2700.0,
        "frequency": "S",
        "label": "Restricao"
    },
    {
        "reservoirCode": 31,
        "uheCode": 45,
        "constraintType": "QDEF",
        "month": 1,
        "minVolume": 0.0,
        "maxVolume": 30.0,
        "minLimit": 0.0,
        "maxLimit": 2700.0,
        "frequency": "S",
        "label": "Restricao"
    },
]
```

Este conjunto de regras informa para o serviço que deve ser construído um reservatório equivalente com o armazenamento das usinas de Furnas (6), Emborcação (24), Nova Ponte (25) e Itumbiara (31). Quando este reservatório se encontrar entre 0% e 30%, a defluência de Jupiá será limitada superiormente a 2700 m3/s. Internamente o serviço cria a representação de um `ReservoirGroupRule` para modelar esta regra:

```json
    {
        "reservoirCodes": [6, 24, 25, 31],
        "uheCode": 45,
        "constraintType": "QDEF",
        "month": 1,
        "minVolume": 0.0,
        "maxVolume": 30.0,
        "minLimit": 0.0,
        "maxLimit": 2700.0,
        "frequency": "S",
        "label": "Restricao"
    },
```

## Arquivos Alterados com as Regras

Em cada um dos modelos energéticos as regras são aplicadas alterando arquivos específicos, informando de modo direto ou indireto a restrição imposta pelas regras operativas.

### NEWAVE

No modelo NEWAVE são alterados principalmente os arquivos `re.dat` e `modif.dat`. Em particular, para casos totalmente individualizados, apenas o arquivo `modif.dat` é necessário, visto que neste é possível informar restrições de mínimo e máximo para ambas as variáveis `QDEF` e `QTUR`. 

Para casos com modelagem agregada, qualquer restrição além de `QDEF` mínimo não é representável, sendo necessário fazer uma aproximação no arquivo `re.dat`. Neste, é utilizada uma aproximação para representar valores máximos de turbinamento e/ou defluência a partir de valores de geração máxima. Valores que superem o engolimento máximo da usina não são representadas, por simplificação, visto que não teriam efeito prático.

De modo mais direto, são alterados os arquivos para cada limite e variável:

- `QDEF` mínimo: `modif.dat`
- `QDEF` máximo: (no momento não incluído no NEWAVE)
- `QTUR` mínimo: `modif.dat`
- `QTUR` máximo: `modif.dat` e `re.dat`


### DECOMP

No modelo DECOMP o único arquivo alterado é o `dadger.rvX`, que contém as informações de todas as restrições de vazão. São editados, ou criados se necessário, os registros `HQ`, `LQ` e `CQ`, informando os códigos de usinas específicos, as variáveis adequadas e os limites impostos por cada regra.


## Rota Fornecida pelo Serviço

A única rota fornecida pelo serviço é `POST /reservoir`, onde o corpo do objeto `JSON` contém o seguinte formato:

```json
{
    "sources": [
        {
        "id": "IgMI7zzpD0irzRysgz7ia2z2KbKEIQEpZ2GpEhUvJGvNxpMlD65iC9oeOQ4",
        "program": "DECOMP"
        }
    ],
    "destination": {
        "id": "IgMI7zzpD0irzRysgz7ia2z2KbKEIQEpZ2GpEhUvJGvNxpMlD65lJjqJqsv",
        "program": "NEWAVE"
    },
    "rules": [
        {
            "reservoirCode": "156",
            "uheCode": 156,
            "constraintType": "QDEF",
            "month": 1.0,
            "minVolume": 0.0,
            "maxVolume": 30.0,
            "minLimit": 100.0,
            "maxLimit": 150.0,
            "frequency": "M",
            "label": "Restricao"
        }
    ]
}
```

Os campos informados são:

- `sources`: Uma lista de casos excutados anteriormente, em ordem cronológica, que podem ser utilizados para extrair uma prospecção de armazenamentos para aplicação das regras. Um caso é resumido a um atributo `id`, que é o caminho para o diretório do caso codificado em `base62`, e um atributo `program` para o nome do programa. Atualmente somente casos de `DECOMP` são suportados para prospecção.  
- `destination`: Um caso, representado da mesma maneira do campo anterior, para ser alvo da aplicação de regras.  
- `rules`: Uma lista de objetos `ReservoirRule`, descritos em uma seção anterior.

A resposta, se flexibilização for realizada com sucesso, contém um objeto com uma lista de `ReservoirGroupRule`, que foram aplicadas ao caso.