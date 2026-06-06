package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.NotNull;
import java.util.List;

@Data
public class App {

    @NotBlank(message = "app.id cannot be empty")
    private String id;

    private String name;

    private String bundle;

    private String storeurl;

    @NotEmpty(message = "app.cat cannot be empty")
    private List<String> cat;

    private String ver;

    private Integer privacypolicy;

    @NotNull(message = "app.publisher cannot be empty")
    private Publisher publisher;

    private String keywords;

    private AppExt ext;

}
