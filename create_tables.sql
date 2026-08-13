DROP TABLE IF EXISTS tb_agendamentos;
DROP TABLE IF EXISTS tb_tipos_agendamento;
DROP TABLE IF EXISTS tb_cids;
DROP TABLE IF EXISTS tb_salas;
DROP TABLE IF EXISTS tb_clinicas;
DROP TABLE IF EXISTS tb_planos;
DROP TABLE IF EXISTS tb_convenios;
DROP TABLE IF EXISTS tb_procedimentos;
DROP TABLE IF EXISTS tb_beneficiarios;
DROP TABLE IF EXISTS tb_especialidades;
DROP TABLE IF EXISTS tb_profissionais;
DROP TABLE IF EXISTS tb_usuarios;

CREATE TABLE IF NOT EXISTS tb_profissionais (
    prof_id BIGINT PRIMARY KEY,
    prof_nome VARCHAR(150),
    prof_conselhonum VARCHAR(20),
    prof_conselhouf VARCHAR(2),
    prof_sexo VARCHAR(1),
    prof_status INT
);

CREATE TABLE IF NOT EXISTS tb_especialidades (
    esp_id BIGINT PRIMARY KEY,
    esp_descricao VARCHAR(100),
    esp_cmed INT
);

CREATE TABLE IF NOT EXISTS tb_beneficiarios (
    benef_id BIGINT PRIMARY KEY,
    benef_nome VARCHAR(150),
    benef_dtnasc DATETIME,
    benef_cpf VARCHAR(11),
    benef_sexo VARCHAR(1),
    benef_numcarteira VARCHAR(30)
);

CREATE TABLE IF NOT EXISTS tb_procedimentos (
    tblproced_id BIGINT PRIMARY KEY,
    proc_codigo BIGINT,
    proc_descricao VARCHAR(200),
    agp_valor DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS tb_convenios (
    conv_ans VARCHAR(20) PRIMARY KEY,
    conv_sigla VARCHAR(30),
    conv_cnpj VARCHAR(14)
);

CREATE TABLE IF NOT EXISTS tb_planos
(
    plano_id        BIGINT PRIMARY KEY,
    plano_descricao VARCHAR(100),
    conv_ans        VARCHAR(20),
    FOREIGN KEY (conv_ans) REFERENCES tb_convenios (conv_ans) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS tb_clinicas (
    cli_id BIGINT PRIMARY KEY,
    cli_corporativo INT
);

CREATE TABLE IF NOT EXISTS tb_salas (
    sala_id BIGINT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS tb_cids (
    tbl_idcid BIGINT PRIMARY KEY,
    cid_id BIGINT
);

CREATE TABLE IF NOT EXISTS tb_tipos_agendamento (
    tpa_id BIGINT PRIMARY KEY,
    tpa_descricao VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS tb_usuarios (
    user_id BIGINT PRIMARY KEY,
    nome VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS tb_agendamentos (
    ag_id BIGINT PRIMARY KEY,
    prof_id BIGINT,
    esp_id BIGINT,
    benef_id BIGINT,
    tblproced_id BIGINT,
    plano_id BIGINT,
    cli_id BIGINT,
    sala_id BIGINT,
    tpa_id BIGINT,
    tbl_idcid BIGINT,
    user_id BIGINT,
    dthoraagenda DATETIME,
    ag_statusagendamento VARCHAR(1),
    FOREIGN KEY (prof_id) REFERENCES tb_profissionais(prof_id),
    FOREIGN KEY (esp_id) REFERENCES tb_especialidades(esp_id),
    FOREIGN KEY (benef_id) REFERENCES tb_beneficiarios(benef_id),
    FOREIGN KEY (tblproced_id) REFERENCES tb_procedimentos(tblproced_id),
    FOREIGN KEY (plano_id) REFERENCES tb_planos(plano_id),
    FOREIGN KEY (cli_id) REFERENCES tb_clinicas(cli_id),
    FOREIGN KEY (sala_id) REFERENCES tb_salas(sala_id),
    FOREIGN KEY (tpa_id) REFERENCES tb_tipos_agendamento(tpa_id),
    FOREIGN KEY (tbl_idcid) REFERENCES tb_cids(tbl_idcid),
    FOREIGN KEY (user_id) REFERENCES tb_usuarios(user_id)
);
