package com.leeyom.scaffold.dto.resp;

import lombok.Data;

import javax.validation.constraints.NotNull;

@Data
public class SkadnExt {

    @NotNull(message = "imp.ext.skadn.ext.sko cannot empty")
    private Integer sko;
}
