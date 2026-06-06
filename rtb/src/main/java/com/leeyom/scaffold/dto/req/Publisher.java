package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import java.util.List;

@Data
public class Publisher {

    @NotBlank(message = "publisher.id cannot be empty")
    private String id;

    private List<String> cat;
}
